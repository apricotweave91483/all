from time import sleep
from datetime import datetime, timedelta
from subprocess import run

print('\n-- POMODORO\n')

rounds = int(input('How many rounds? '))
rlength = float(input('How many minutes per round? '))
brk = float(input('Minutes per break? '))


OS_MEDIA_PLAYER = "paplay"
aud = "bell-window-system.oga"

for x in range(rounds):
	if x != 0:
		run(['{}'.format(OS_MEDIA_PLAYER),aud])
		input('Round over. Press enter to start your break...')
		break_mins_from_now = datetime.now() + timedelta(minutes=brk)
		print("\n-- BREAK:\n")
		print(f'You have until {break_mins_from_now.strftime("%H:%M")}')
		sleep(60 * brk)
		run(['{}'.format(OS_MEDIA_PLAYER),aud])
		input(f'Break over. Press enter to start round {x+1}...')
	else:
		input(f'Press enter to start round {x+1}...')
	work_mins_from_now = datetime.now() + timedelta(minutes=rlength)
	print("\n-- WORK:\n")
	print(f'Work until {work_mins_from_now.strftime("%H:%M")}')
	sleep(60 * rlength)

run(['{}'.format(OS_MEDIA_PLAYER),aud])
print('Pomodoro over. Good Job!')
print('\n-- POMODORO\n')

