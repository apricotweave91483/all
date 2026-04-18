"""
Board collection / computer vision for 2048.
Calibration, screenshots, color sampling, matching to 2048_colors.json,
and read_board() that returns a 4x4 grid of tile values.
"""

import json
import os
import time
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pyautogui


BOARD_SIZE = 4


@dataclass
class BoardRegion:
    left: int
    top: int
    width: int
    height: int
    sample_dx: float = 0.0
    sample_dy: float = 0.0
    sample_box: int = 24  # larger patch = more averaging, stabler color for tiles like 2

    @property
    def cell_w(self) -> float:
        return self.width / BOARD_SIZE

    @property
    def cell_h(self) -> float:
        return self.height / BOARD_SIZE


# Initial RGB guesses; extended from 2048_colors.json and interactively.
TILE_COLORS = {
    0: (180, 162, 142),
    2: (210, 198, 187),
    4: (231, 211, 176),
}

COLORS_JSON_PATH = os.path.join(os.path.dirname(__file__), "2048_colors.json")
# Squared RGB distance: higher = accept more variation (2 tile often has gradient/text)
COLOR_DIST_THRESHOLD = 35 ** 2
JUST_LEARNED_COLOR = False


def load_saved_colors() -> None:
    """Load previously learned tile colors from JSON, if present."""
    global TILE_COLORS
    try:
        with open(COLORS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        loaded = {int(k): tuple(map(int, v)) for k, v in data.items()}
        TILE_COLORS.update(loaded)
        if loaded:
            print(f"Loaded {len(loaded)} saved tile colors from 2048_colors.json")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Warning: could not load 2048_colors.json: {e}")


def save_colors() -> None:
    """Persist current TILE_COLORS to JSON."""
    try:
        serializable = {str(k): list(v) for k, v in TILE_COLORS.items()}
        with open(COLORS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save 2048_colors.json: {e}")


def wait_for_focus() -> None:
    print(
        "Make sure the 2048 window is visible and active.\n"
        "The bot will use pyautogui to read pixels and send arrow keys.\n"
    )
    input("When ready, press Enter here to begin calibration...")


def calibrate_board() -> BoardRegion:
    print(
        "Calibration: do TOP-LEFT twice, then BOTTOM-RIGHT twice (so you don't re-aim):\n"
        "1) TOP-LEFT tile center, press Enter.\n"
        "2) TOP-LEFT safe spot (background, not on number), press Enter.\n"
        "3) BOTTOM-RIGHT tile center, press Enter.\n"
        "4) BOTTOM-RIGHT safe spot (background, not on number), press Enter.\n"
    )
    input("Hover over TOP-LEFT tile center, then press Enter...")
    x1, y1 = pyautogui.position()
    print(f"Captured TOP-LEFT at ({x1}, {y1})")

    input("Now TOP-LEFT safe spot (same tile, away from number), then press Enter...")
    sx1, sy1 = pyautogui.position()
    print(f"Captured TOP-LEFT sample spot at ({sx1}, {sy1})")

    input("Now hover over BOTTOM-RIGHT tile center, then press Enter...")
    x2, y2 = pyautogui.position()
    print(f"Captured BOTTOM-RIGHT at ({x2}, {y2})")

    input("Now BOTTOM-RIGHT safe spot (same tile, away from number), then press Enter...")
    sx2, sy2 = pyautogui.position()
    print(f"Captured BOTTOM-RIGHT sample spot at ({sx2}, {sy2})")

    dx = x2 - x1
    dy = y2 - y1
    cell_w = dx / (BOARD_SIZE - 1)
    cell_h = dy / (BOARD_SIZE - 1)

    left = int(round(x1 - cell_w / 2))
    top = int(round(y1 - cell_h / 2))
    width = int(round(cell_w * BOARD_SIZE))
    height = int(round(cell_h * BOARD_SIZE))

    sample_dx = ((sx1 - x1) + (sx2 - x2)) / 2.0
    sample_dy = ((sy1 - y1) + (sy2 - y2)) / 2.0

    region = BoardRegion(
        left=left,
        top=top,
        width=width,
        height=height,
        sample_dx=sample_dx,
        sample_dy=sample_dy,
    )
    print(
        f"Inferred board region: left={region.left}, top={region.top}, "
        f"width={region.width}, height={region.height}"
    )
    print(
        f"Sampling offset (relative to each tile center): dx={region.sample_dx:.1f}, dy={region.sample_dy:.1f} "
        f"(sample_box={region.sample_box}px)"
    )
    return region


def grab_board_image(region: BoardRegion):
    shot = pyautogui.screenshot(
        region=(region.left, region.top, region.width, region.height)
    )
    img = np.array(shot)
    if img.shape[2] == 4:
        img = img[:, :, :3]
    img = img[:, :, ::-1]
    return img


def average_color(img, margin_ratio: float = 0.2) -> Tuple[float, float, float]:
    h, w, _ = img.shape
    mx = int(w * margin_ratio)
    my = int(h * margin_ratio)
    roi = img[my : h - my, mx : w - mx]
    roi_rgb = roi[:, :, ::-1]
    mean = roi_rgb.mean(axis=(0, 1))
    return float(mean[0]), float(mean[1]), float(mean[2])


def sample_patch_mean_rgb(board_bgr, cx: int, cy: int, box: int) -> Tuple[float, float, float]:
    h, w, _ = board_bgr.shape
    half = max(1, box // 2)
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w, cx + half)
    y2 = min(h, cy + half)
    patch = board_bgr[y1:y2, x1:x2]
    if patch.size == 0:
        return 0.0, 0.0, 0.0
    patch_rgb = patch[:, :, ::-1]
    mean = patch_rgb.mean(axis=(0, 1))
    return float(mean[0]), float(mean[1]), float(mean[2])


def closest_tile_value(rgb: Tuple[float, float, float]) -> Tuple[int, float]:
    r, g, b = rgb
    best_val = 0
    best_dist = float("inf")
    for val, (tr, tg, tb) in TILE_COLORS.items():
        dr = r - tr
        dg = g - tg
        db = b - tb
        dist = dr * dr + dg * dg + db * db
        if dist < best_dist:
            best_dist = dist
            best_val = val
    return best_val, best_dist


def classify_or_learn_tile(
    rgb: Tuple[float, float, float], row_idx: int, col_idx: int
) -> int:
    global JUST_LEARNED_COLOR

    best_val, best_dist = closest_tile_value(rgb)
    if best_dist <= COLOR_DIST_THRESHOLD:
        return best_val

    r, g, b = rgb
    print(
        f"\n[Calib] row {row_idx + 1}, col {col_idx + 1} "
        f"RGB=({r:.0f},{g:.0f},{b:.0f}) → nearest={best_val}"
    )
    ans = input(
        "Value there? (0 empty, Enter=0; n/none/skip = ignore, treat as empty, continue): "
    ).strip().lower()

    if ans in ("n", "none", "skip", "no"):
        JUST_LEARNED_COLOR = True
        print("Ignoring tile (treating as empty). Refocus the game window during countdown.")
        return 0
    if ans == "":
        val = 0
    else:
        try:
            val = int(ans)
        except ValueError:
            print("Could not parse input, defaulting to 0.")
            val = 0

    TILE_COLORS[val] = (int(round(r)), int(round(g)), int(round(b)))
    save_colors()
    JUST_LEARNED_COLOR = True
    print(f"Learned mapping: value {val} -> RGB {TILE_COLORS[val]}")
    return val


def read_board(region: BoardRegion) -> List[List[int]]:
    img = grab_board_image(region)
    grid: List[List[int]] = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell_cx = int(round((c + 0.5) * region.cell_w))
            cell_cy = int(round((r + 0.5) * region.cell_h))
            sample_x = int(round(cell_cx + region.sample_dx))
            sample_y = int(round(cell_cy + region.sample_dy))
            rgb = sample_patch_mean_rgb(img, sample_x, sample_y, region.sample_box)
            val = classify_or_learn_tile(rgb, r, c)
            grid[r][c] = val
    return grid


def print_board(grid: List[List[int]]) -> None:
    print("\nBoard:")
    for row in grid:
        print(" ".join(f"{v:4d}" for v in row))


def manual_color_correction(region: BoardRegion) -> None:
    """
    Pause and let user manually correct tile colors by clicking on tiles.
    User positions mouse over a tile, presses Enter, then enters what value it should be.
    Continues until user types 'done' or 'q'.
    """
    global TILE_COLORS, JUST_LEARNED_COLOR

    print(
        "\n=== MANUAL COLOR CORRECTION MODE ===\n"
        "Position your mouse over a tile, press Enter, then tell me what value it is.\n"
        "Type 'done' or 'q' when finished.\n"
    )
    input("Press Enter when ready...")

    while True:
        print("\nPosition mouse over a tile, then press Enter (or type 'done'/'q' to finish):")
        try:
            ans = input("> ").strip().lower()
            if ans in ("done", "q", "quit"):
                break
            
            # Capture mouse position immediately after Enter
            x, y = pyautogui.position()
            print(f"Captured position: ({x}, {y})")

            # Sample RGB at that position
            img = grab_board_image(region)
            # Convert click position to board-image coordinates
            rel_x = x - region.left
            rel_y = y - region.top
            
            # Check if position is within board bounds
            if rel_x < 0 or rel_x >= region.width or rel_y < 0 or rel_y >= region.height:
                print(f"Warning: Position ({x}, {y}) is outside board region!")
                continue
                
            rgb = sample_patch_mean_rgb(img, int(rel_x), int(rel_y), region.sample_box)
            r, g, b = rgb

            print(f"RGB at ({x}, {y}): ({r:.0f}, {g:.0f}, {b:.0f})")
            val_str = input("What value is this tile? (or 'skip'/'done'/'q' to skip/finish): ").strip().lower()
            
            if val_str in ("done", "q", "quit"):
                break
            if val_str in ("skip", "s", ""):
                print("Skipped.")
                continue

            try:
                val = int(val_str)
            except ValueError:
                print("Invalid value, skipping.")
                continue

            old_rgb = TILE_COLORS.get(val)
            TILE_COLORS[val] = (int(round(r)), int(round(g)), int(round(b)))
            save_colors()
            if old_rgb:
                print(f"✓ Updated: value {val} -> RGB {TILE_COLORS[val]} (was {old_rgb})")
            else:
                print(f"✓ Added: value {val} -> RGB {TILE_COLORS[val]}")
            JUST_LEARNED_COLOR = True

        except KeyboardInterrupt:
            print("\nCorrection mode cancelled.")
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\n=== Exiting correction mode. Bot will resume shortly. ===\n")
