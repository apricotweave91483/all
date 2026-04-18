Usage: fetch [OPTIONS]

Get a random Codeforces problem by difficulty range, or open a specific problem.

Uses jq and the Codeforces API

Options:
```bash
  -d, --difficulty RANGE    Difficulty range (e.g. "800-1200" or "800")
  -p, --problem ID          Open a specific problem by ID (e.g. "1520A")
      --allow-repeat        Allow problems that have been seen before
      --no-save             Don't save this problem to the seen list
      --clear-seen          Clear the seen problems list
      --stats               Show statistics about seen problems
      --open                Open the problem in the default web browser
      --mark-complete ID    Mark a problem as completed (e.g. 151A)
      --remove ID           Remove a problem from the seen list (e.g. 151A)
  -h [N], --history [N]     Show the last N fetched problems (default 10)
      --help                Show this help message and exit
```
```bash
  fetch --difficulty 800-1200
  fetch -d 1500-2000
  fetch -d 800 --allow-repeat
  fetch -d 1200-1600 --no-save
  fetch -d 800-1200 --open
  fetch --problem 1520A
  fetch -p 292A --open
  fetch --mark-complete 151A
  fetch --remove 151A
  fetch -h 20
```
