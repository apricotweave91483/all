from os import system
from random import random
from pathlib import Path
script_dir = Path(__file__).resolve().parent
sender_script = "weekly_cses_sender.py"

if random() > (2/3):
    system("python3 " + str(script_dir) + "/" + sender_script)

