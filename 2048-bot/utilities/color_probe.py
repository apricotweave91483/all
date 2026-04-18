import time
from typing import Tuple

import numpy as np
import pyautogui


def sample_color_around_mouse(box_size: int = 18) -> Tuple[float, float, float]:
    """Sample a small square around the mouse and return mean RGB."""
    x, y = pyautogui.position()
    half = box_size // 2
    left = x - half
    top = y - half
    shot = pyautogui.screenshot(region=(left, top, box_size, box_size))
    arr = np.array(shot)
    if arr.shape[2] == 4:
        arr = arr[:, :, :3]
    mean = arr.mean(axis=(0, 1))
    r, g, b = float(mean[0]), float(mean[1]), float(mean[2])
    return r, g, b


def main():
    print(
        "2048 color probe\n"
        "- Move your mouse over a tile background (avoid the number itself).\n"
        "- Press Enter to sample the color at the cursor.\n"
        "- Ctrl+C to quit.\n"
    )

    while True:
        try:
            input("Hover over target tile and press Enter...")
            r, g, b = sample_color_around_mouse()
            print(f"RGB≈({r:.1f}, {g:.1f}, {b:.1f})  int=({int(r)}, {int(g)}, {int(b)})")
            time.sleep(0.2)
        except KeyboardInterrupt:
            print("\nExiting color probe.")
            break


if __name__ == "__main__":
    main()

