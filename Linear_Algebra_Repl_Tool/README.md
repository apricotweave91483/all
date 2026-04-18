# linear algebra repl tool

## what this is

a small linear algebra / exact arithmetic playground in python.

it gives you:
- a custom `Fraction` type for exact values
- `Vector` and `Matrix` classes
- `System` for linear systems (augmented matrix style)
- some helper ops like gram-schmidt

it is built for quick repl use, so some method names are short on purpose (`FS`, `FI`).

## quick start

run python and import from `LA.py`.

```python
from LA import Fraction, Vector, Matrix, System, Ops
```

## parsing / input (the short names)

the matrix parser/input helpers were renamed:

- `Matrix.FS(...)` = matrix from string
- `Matrix.FI(...)` = matrix from interactive input

same idea for systems:

- `System.FS(...)`
- `System.FI(...)`

## examples

```python
from LA import Matrix, Vector, System

# matrix from string
A = Matrix.FS("1 2\n3 4")

# matrix from multiline string with row count first
B = Matrix.FS("2\n1 2\n3 4")

# matrix-vector multiply
v = Vector([1, 1])
Av = A * v

# get float tuple from vector components
vf = Vector(["1/2", "2", "3/4"]).floats()

# row reduction
R = A.rref()

# determinant / inverse / rank
d = A.determinant()
A_inv = A.inverse()
r = A.rank()

# matrix powers (good for markov transitions)
A10 = A ** 10
# negative power works too (inverse power)
A_inv2 = A ** -2

# solve a system (augmented matrix: last col is rhs)
S = System.FS("1 2 5\n3 4 11")
ans = S.solution()
S.solve()  # prints a readable version
```

## matrix string formats

`Matrix.FS` accepts a few formats:

- multiline rows: `"1 2 3\n4 5 6"`
- optional row count first: `"2\n1 2\n3 4"`
- python list style: `"[[1, 2], [3, 4]]"`
- comma-separated rows also work

## notes

- values are converted to `Fraction` where possible
- decimals are supported, but exactness depends on how they are parsed into fractions
- `System` treats the last column as the constant/right-hand side column

## file

everything is currently in:

- `LA.py`

