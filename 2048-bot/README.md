### What to do

From the 2048-bot directory:

make a venv: python3 -m venv 2048env

activate the venv: source 2048env/bin/activate

install the requirements: pip3 install -r requirements.txt 

### Then go to the "app" directory

compile the C program: gcc -O3 -march=native -o strategy_2048 strategy_2048.c -lm -lpthread

run the bot: python3 bot_2048.py

---

**Directory layout**

```
2048-bot/
├── README.md
├── requirements.txt
├── app/
│   ├── bot_2048.py          # main script
│   ├── board_vision.py      # calibration, screen grab, color matching
│   ├── strategy_2048.c      # expectimax search (compile → strategy_2048 binary)
│   └── 2048_colors.json     # tile value → RGB; loaded and updated by the bot
└── utilities/
    └── color_probe.py       # hover over a tile, Enter → print RGB for the JSON
```

---

### Summary

The bot plays 2048 on play2048.co. It grabs the board from the screen (pyautogui), matches tile colors to values using 2048_colors.json, then picks a move. The heavy search (expectimax) runs in the compiled C binary; Python just reads the board and sends arrow keys.

2048_colors.json lives in app/ and stores one RGB per tile value (0, 2, 4, 8, …). The bot loads it at startup. When it sees a color it doesn’t recognize, it asks you what value it is and saves that to the JSON so next time it knows. You can also correct colors while the bot is running: press P to pause, then position the mouse over a tile, press Enter, type the correct value (e.g. 256), and the bot updates that RGB in the JSON and resumes.

utilities/color_probe.py is a helper: run it (python3 utilities/color_probe.py), move the mouse over a tile, press Enter, and it prints the RGB at the cursor so you can add or fix an entry in 2048_colors.json by hand if you want.

Each time you start the script you calibrate: you move the mouse to the top-left tile center, then a safe spot on that tile, then the bottom-right tile center, then a safe spot on that tile. The bot uses that to find the board and where to sample color in each cell. After calibration you get a short countdown to focus the game window; then it starts playing.

Press Ctrl+C in the terminal to stop. If the board stops changing for several moves the bot stops on its own.
