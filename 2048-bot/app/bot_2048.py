"""
2048 bot master script.
Uses board_vision for calibration and reading the board (CV + color matching).
Orchestrates: read board → get move (Python strategy or spawn C binary) → press key.
"""

import os
import subprocess
import threading
import time
from typing import List, Optional, Tuple
import abc

import pyautogui
from pynput import keyboard

import board_vision
from board_vision import (
    BOARD_SIZE,
    BoardRegion,
    calibrate_board,
    load_saved_colors,
    print_board,
    read_board,
    wait_for_focus,
)


Grid = List[List[int]]


def move_left(grid: Grid):
    new_grid: Grid = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    total_score = 0
    changed = False

    for r in range(BOARD_SIZE):
        row = grid[r]
        compressed = [v for v in row if v != 0]
        merged_row: List[int] = []
        skip = False
        i = 0
        while i < len(compressed):
            if not skip and i + 1 < len(compressed) and compressed[i] == compressed[i + 1]:
                merged_val = compressed[i] * 2
                total_score += merged_val
                merged_row.append(merged_val)
                skip = True
            else:
                if not skip:
                    merged_row.append(compressed[i])
                skip = False
            i += 1
            if skip:
                skip = False
                i += 0
        merged_row += [0] * (BOARD_SIZE - len(merged_row))
        new_grid[r] = merged_row
        if merged_row != row:
            changed = True

    return new_grid, total_score, changed


def rotate_grid(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid[::-1])]


def move(grid: Grid, direction: str):
    g = [row[:] for row in grid]
    if direction == "left":
        return move_left(g)
    elif direction == "right":
        g = rotate_grid(rotate_grid(g))
        moved, score, changed = move_left(g)
        moved = rotate_grid(rotate_grid(moved))
        return moved, score, changed
    elif direction == "up":
        g = rotate_grid(rotate_grid(rotate_grid(g)))
        moved, score, changed = move_left(g)
        moved = rotate_grid(moved)
        return moved, score, changed
    elif direction == "down":
        g = rotate_grid(g)
        moved, score, changed = move_left(g)
        moved = rotate_grid(rotate_grid(rotate_grid(moved)))
        return moved, score, changed
    else:
        raise ValueError(direction)


class Strategy(abc.ABC):
    @abc.abstractmethod
    def choose_move(self, grid: Grid) -> Optional[str]:
        raise NotImplementedError


class HeuristicStrategy(Strategy):
    def _count_empty(self, grid: Grid) -> int:
        return sum(1 for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if grid[r][c] == 0)

    def _max_tile(self, grid: Grid) -> int:
        return max(max(row) for row in grid)

    def _corner_score(self, grid: Grid) -> int:
        m = self._max_tile(grid)
        corners = [grid[0][0], grid[0][BOARD_SIZE - 1], grid[BOARD_SIZE - 1][0], grid[BOARD_SIZE - 1][BOARD_SIZE - 1]]
        return 1000 if m in corners else 0

    def _monotonicity_score(self, grid: Grid) -> int:
        def line_score(line):
            items = [v for v in line if v != 0]
            if len(items) <= 1:
                return 0
            inc = all(items[i] <= items[i + 1] for i in range(len(items) - 1))
            dec = all(items[i] >= items[i + 1] for i in range(len(items) - 1))
            return 5 if inc or dec else 0

        score = 0
        for r in range(BOARD_SIZE):
            score += line_score(grid[r])
        for c in range(BOARD_SIZE):
            score += line_score([grid[r][c] for r in range(BOARD_SIZE)])
        return score

    def _heuristic(self, grid: Grid, gained_score: int) -> float:
        empties = self._count_empty(grid)
        corner = self._corner_score(grid)
        mono = self._monotonicity_score(grid)
        return gained_score * 1.0 + empties * 10.0 + corner * 1.0 + mono * 2.0

    def choose_move(self, grid: Grid) -> Optional[str]:
        directions = ["up", "left", "right", "down"]
        best_dir: Optional[str] = None
        best_score = float("-inf")
        for d in directions:
            new_grid, gained, changed = move(grid, d)
            if not changed:
                continue
            h = self._heuristic(new_grid, gained)
            if h > best_score:
                best_score = h
                best_dir = d
        return best_dir


class LookaheadStrategy(HeuristicStrategy):
    def __init__(self, depth: int = 3, gamma: float = 0.9):
        self.depth = depth
        self.gamma = gamma

    def _search(self, grid: Grid, depth: int) -> float:
        if depth == 0:
            return self._heuristic(grid, gained_score=0)

        best = float("-inf")
        any_move = False
        for d in ("up", "left", "right", "down"):
            new_grid, gained, changed = move(grid, d)
            if not changed:
                continue
            any_move = True
            score_here = self._heuristic(new_grid, gained)
            score_future = self._search(new_grid, depth - 1)
            total = score_here + self.gamma * score_future
            if total > best:
                best = total

        if not any_move:
            return self._heuristic(grid, gained_score=0)
        return best

    def choose_move(self, grid: Grid) -> Optional[str]:
        best_dir: Optional[str] = None
        best_score = float("-inf")

        for d in ("up", "left", "right", "down"):
            new_grid, gained, changed = move(grid, d)
            if not changed:
                continue
            score_here = self._heuristic(new_grid, gained)
            score_future = self._search(new_grid, self.depth - 1) if self.depth > 1 else 0.0
            total = score_here + self.gamma * score_future
            if total > best_score:
                best_score = total
                best_dir = d
        return best_dir


def _grid_key(grid: Grid):
    return tuple(tuple(row) for row in grid)


class ExpectimaxStrategy(HeuristicStrategy):
    def __init__(
        self,
        depth_low: int = 4,
        depth_high: int = 8,
        gamma: float = 0.95,
        max_empty_samples: int = 10,
        serious_empty_threshold: int = 5,
        serious_max_tile: int = 1024,
    ):
        self.depth_low = depth_low
        self.depth_high = depth_high
        self.gamma = gamma
        self.max_empty_samples = max_empty_samples
        self.serious_empty_threshold = serious_empty_threshold
        self.serious_max_tile = serious_max_tile
        self._cache: dict = {}

    def _empty_cells(self, grid: Grid) -> List[Tuple[int, int]]:
        return [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if grid[r][c] == 0]

    def _smoothness_score(self, grid: Grid) -> float:
        penalty = 0.0
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                val = grid[r][c]
                if val == 0:
                    continue
                if c + 1 < BOARD_SIZE:
                    neighbor = grid[r][c + 1]
                    if neighbor != 0:
                        penalty += abs(val - neighbor)
                if r + 1 < BOARD_SIZE:
                    neighbor = grid[r + 1][c]
                    if neighbor != 0:
                        penalty += abs(val - neighbor)
        return -penalty

    def _eval(self, grid: Grid) -> float:
        empties = self._count_empty(grid)
        corner = self._corner_score(grid)
        mono = self._monotonicity_score(grid)
        smooth = self._smoothness_score(grid)
        max_val = self._max_tile(grid)
        return (
            empties * 15.0
            + corner * 2.5
            + mono * 4.0
            + smooth * 0.1
            + max_val * 0.01
        )

    def _expectimax(self, grid: Grid, depth: int, is_max: bool) -> float:
        key = (_grid_key(grid), depth, is_max)
        if key in self._cache:
            return self._cache[key]

        if depth == 0:
            v = self._eval(grid)
            self._cache[key] = v
            return v

        empties = self._empty_cells(grid)
        if not empties:
            v = self._eval(grid)
            self._cache[key] = v
            return v

        if is_max:
            best = float("-inf")
            any_move = False
            for d in ("up", "left", "right", "down"):
                new_grid, gained, changed = move(grid, d)
                if not changed:
                    continue
                any_move = True
                score_here = self._eval(new_grid) + gained * 0.1
                future = self._expectimax(new_grid, depth - 1, False)
                total = score_here + self.gamma * future
                if total > best:
                    best = total
            if not any_move:
                best = self._eval(grid)
            self._cache[key] = best
            return best
        else:
            cells = empties
            if len(cells) > self.max_empty_samples:
                cells = sorted(cells, key=lambda rc: rc[0], reverse=True)[: self.max_empty_samples]
            expected = 0.0
            total_prob = 0.0
            for (r, c) in cells:
                for value, prob in ((2, 0.9), (4, 0.1)):
                    grid2 = [row[:] for row in grid]
                    grid2[r][c] = value
                    val = self._expectimax(grid2, depth - 1, True)
                    expected += prob * val
                    total_prob += prob
            if total_prob == 0.0:
                result = self._eval(grid)
            else:
                result = expected / total_prob
            self._cache[key] = result
            return result

    def choose_move(self, grid: Grid) -> Optional[str]:
        self._cache.clear()
        empties = self._count_empty(grid)
        max_tile = self._max_tile(grid)
        serious = (
            empties <= self.serious_empty_threshold
            or max_tile >= self.serious_max_tile
        )
        depth = self.depth_high if serious else self.depth_low

        best_dir: Optional[str] = None
        best_score = float("-inf")
        for d in ("up", "left", "right", "down"):
            new_grid, gained, changed = move(grid, d)
            if not changed:
                continue
            score_here = self._eval(new_grid) + gained * 0.1
            future = self._expectimax(new_grid, depth - 1, False)
            total = score_here + self.gamma * future
            if total > best_score:
                best_score = total
                best_dir = d
        self._last_depth = depth
        return best_dir


class CStrategy(Strategy):
    """Spawns compiled strategy_2048 binary; passes grid via stdin, reads move from stdout."""

    def __init__(
        self,
        binary_path: Optional[str] = None,
        depth_low: int = 4,
        depth_high: int = 9,
        serious_empty_threshold: int = 5,
        serious_max_tile: int = 512,
        max_empty_samples: int = 10,
        timeout_seconds: float = 30.0,
        search_timeout_sec: int = 4,
    ):
        if binary_path is None:
            binary_path = os.path.join(os.path.dirname(__file__), "strategy_2048")
        self.binary_path = binary_path
        self.depth_low = depth_low
        self.depth_high = depth_high
        self.serious_empty_threshold = serious_empty_threshold
        self.serious_max_tile = serious_max_tile
        self.max_empty_samples = max_empty_samples
        self.timeout_seconds = timeout_seconds
        self.search_timeout_sec = search_timeout_sec

    def choose_move(self, grid: Grid) -> Optional[str]:
        if not os.path.isfile(self.binary_path):
            return None
        grid_str = "\n".join(
            " ".join(str(grid[r][c]) for c in range(BOARD_SIZE))
            for r in range(BOARD_SIZE)
        )
        argv = [
            self.binary_path,
            str(self.depth_low),
            str(self.depth_high),
            str(self.serious_empty_threshold),
            str(self.serious_max_tile),
            str(self.max_empty_samples),
            str(self.search_timeout_sec),
        ]
        try:
            result = subprocess.run(
                argv,
                input=grid_str,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=os.path.dirname(self.binary_path) or ".",
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
        out = (result.stdout or "").strip().lower()
        empties = sum(1 for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if grid[r][c] == 0)
        max_tile = max(max(row) for row in grid)
        serious = empties <= self.serious_empty_threshold or max_tile >= self.serious_max_tile
        self._last_depth = self.depth_high if serious else self.depth_low
        if out in ("up", "down", "left", "right"):
            return out
        if out == "none":
            return None
        return None


# Global flag for pause-and-recalibrate triggered by key press
_recalibrate_requested = False
_recalibrate_lock = threading.Lock()


def _on_key_press(key):
    """Handle key press: 'p' triggers recalibration."""
    global _recalibrate_requested
    try:
        if hasattr(key, 'char') and key.char == 'p':
            with _recalibrate_lock:
                _recalibrate_requested = True
    except AttributeError:
        pass


def play_loop(region: BoardRegion, strategy: Strategy, delay: float = 0.08) -> None:
    global _recalibrate_requested

    # Start keyboard listener in background thread
    listener = keyboard.Listener(on_press=_on_key_press)
    listener.start()
    play_loop._listener = listener  # Store for cleanup

    last_grid = None
    stagnant_steps = 0
    max_stagnant = 8
    step = 0

    while True:
        # Check for pause-and-recalibrate trigger (key 'p' pressed)
        with _recalibrate_lock:
            if _recalibrate_requested:
                _recalibrate_requested = False
                print("\n[PAUSE] 'P' key pressed. Pausing for manual color correction...")
                try:
                    board_vision.manual_color_correction(region)
                finally:
                    pass
                print("Resuming bot in 3 seconds...")
                for i in range(3, 0, -1):
                    print(f"{i}...")
                    time.sleep(1)

        grid = read_board(region)

        if board_vision.JUST_LEARNED_COLOR:
            board_vision.JUST_LEARNED_COLOR = False
            print(
                "\nNew tile color learned. You now have a moment to click/focus "
                "the 2048 window again before the bot resumes."
            )
            for i in range(3, 0, -1):
                print(f"Resuming in {i}...")
                time.sleep(1)

        print_board(grid)

        if last_grid is not None and grid == last_grid:
            stagnant_steps += 1
        else:
            stagnant_steps = 0
        last_grid = grid

        if stagnant_steps >= max_stagnant:
            print("Board not changing for several moves. Stopping.")
            break

        direction = strategy.choose_move(grid)
        if direction is None:
            print("No valid moves found. Stopping.")
            break

        depth = getattr(strategy, "_last_depth", None)
        if depth is not None:
            print(f"Step {step}: depth = {depth}, pressing {direction.upper()}")
        else:
            print(f"Step {step}: pressing {direction.upper()}")
        pyautogui.press(direction)
        step += 1
        time.sleep(delay)

    # Cleanup: stop keyboard listener when loop exits
    try:
        listener.stop()
    except:
        pass


def main() -> None:
    load_saved_colors()
    wait_for_focus()
    region = calibrate_board()
    input(
        "\nCalibration complete.\n"
        "When you press Enter here, you will get a short countdown.\n"
        "Use that time to click/focus the 2048 window.\n"
        "Press Enter to arm the countdown..."
    )

    countdown = 5
    for i in range(countdown, 0, -1):
        print(f"Starting in {i}... (click the 2048 window now)")
        time.sleep(1)

    print("\nStarting 2048 bot. Press Ctrl+C in this terminal to stop.")
    print("Press 'P' key at any time to pause and correct tile colors.\n")
    c_binary = os.path.join(os.path.dirname(__file__), "strategy_2048")
    if os.path.isfile(c_binary):
        strategy: Strategy = CStrategy(
            binary_path=c_binary,
            depth_low=4,
            depth_high=9,
            serious_empty_threshold=5,
            serious_max_tile=512,
            max_empty_samples=10,
            search_timeout_sec=4,
        )
        print("Using C strategy (strategy_2048, depth up to 9, 4s search budget).")
    else:
        strategy = ExpectimaxStrategy(
            depth_low=4,
            depth_high=8,
            gamma=0.95,
            max_empty_samples=10,
            serious_empty_threshold=6,
            serious_max_tile=512,
        )
        print("Using Python expectimax strategy (C binary not found).")
    try:
        play_loop(region, strategy)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Cleanup: stop keyboard listener if it exists
        if hasattr(play_loop, '_listener'):
            try:
                play_loop._listener.stop()
            except:
                pass


if __name__ == "__main__":
    main()
