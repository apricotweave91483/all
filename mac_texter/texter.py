#!/usr/bin/env python3

from time import sleep
from pyautogui import hotkey, press, write
from sys import argv

mod : str = 'command'

sleep(1.5)

hotkey(mod,'space')

sleep(1)

write('message')

sleep(1.5)

press('enter')

if len(argv) > 1:
	sleep(4)
	hotkey(mod,'n')
	sleep(.5)
	i = 1
	while argv[i] != "-MSG":
		write(argv[i])
		sleep(.9)
		press('enter')
		sleep(.25)
		i += 1
		if i == len(argv):
			press('enter')
			exit(0)
	press('enter')
	sleep(.5)
	if i+1 < len(argv):
		write(argv[i+1])
		press('enter')
