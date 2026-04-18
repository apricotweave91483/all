usage: clink [-h] [-o OUTPUT] source helpers [helpers ...]

Inject canned helper functions into a C source file.

positional arguments:
  source               Input C file path
  helpers              Helper names to inject

options:
  -h, --help           show this help message and exit
  -o, --output OUTPUT  Output file path (default: overwrite input source)

Available helpers:
  icmp: Compare two int values for qsort/bsearch.
  llcmp: Compare two long long values for qsort/bsearch.
