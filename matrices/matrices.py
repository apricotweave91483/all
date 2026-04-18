# Handrwitten, BTW, first iteration of the Linear Algebra library, i thought it would be a nice exercise to try and writ the routine myself after learning about the algorithm in linear algebra class, then after doing that as an exercise and enjoying the fun of writing boilerplate and being able to implement something useful i learned in a class, I decided i wanted to level up to a real REPL library with some more functionality, so I vibe coded the next iteration, called "Linear_Algebra_Repl_Tool"

from fractions import Fraction
import numpy as np

class Matrix:
    def __init__(self, dt, _input=None):
        if dt == "F":
            self.DTYPE = Fraction
        elif dt == "D":
            self.DTYPE = np.float64
        else:
            exit(1)
        if _input != None:
            self.SYSTEM = np.array(_input, dtype=self.DTYPE)
            self.total_row = len(self.SYSTEM)
            self.total_column = len(self.SYSTEM[0])

    def input_matrix(self):
        self.SYSTEM = np.array([list(map(self.DTYPE, input().split())) for i in range(int(input()))])
        self.total_row = len(self.SYSTEM)
        self.total_column = len(self.SYSTEM[0])

    def show(self):
        for row in self.SYSTEM:
            for x in row:
                print(str(x), end="  ")
            print()

    def first_nonzero(self, array):
        z = (np.nonzero(array))[0]

        if z.size:
            return z[0]

        return np.inf

    def make_swap(self, start):
        F = self.first_nonzero(self.SYSTEM[start])
        L = None
        G = 0

        for i in range(start + 1, len(self.SYSTEM)):
            L = self.first_nonzero(self.SYSTEM[i])
            if L < F:
                G = 1
                break

        if G:
            self.SYSTEM[[i, start]] = self.SYSTEM[[start, i]]
            return

        return

    def ref(self):

        curr_row = 0
        curr_column = 0

        while curr_row < self.total_row and curr_column < self.total_column:
            self.make_swap(curr_row)

            if self.SYSTEM[curr_row][curr_column] == 0:
                curr_column += 1
                continue

            self.SYSTEM[curr_row] /= self.SYSTEM[curr_row][curr_column]
            for i in range(curr_row + 1, self.total_row):
                self.SYSTEM[i] -= (self.SYSTEM[i][curr_column] * self.SYSTEM[curr_row])
    
            curr_row += 1
            curr_column += 1

    def find_pivots(self) -> set[tuple]:
        # Only works if REF already

        pivots = set()

        for row_num, row in enumerate(self.SYSTEM):
            for i, x in enumerate(row):
                if x:
                    pivots.add((row_num, i))
                    break

        return pivots

    def rref(self):

        pivots = self.find_pivots()

        for pivot in pivots:
            r, c = pivot[0], pivot[1]
            for i in range(r - 1, -1, -1):
                self.SYSTEM[i] -= (self.SYSTEM[r] * self.SYSTEM[i][c])

        return

    def parameterize_infinite_solutions(self):
        pivots = self.find_pivots()

        basic = set()
        for pivot in pivots:
            basic.add(pivot[1])
        free = set(v for v in range(self.total_column - 1) if not v in basic)

        maps = {}

        for f in free:
            t = [0] * (self.total_column) 
            t[f] = 1
            maps[f] = tuple(t)

        for pivot in pivots:
            t = list(self.SYSTEM[pivot[0]])
            for x in range(self.total_column - 1):
                t[x] *= -1
            maps[pivot[1]] = tuple(t)
    
        rep = []
    
        rep.append(tuple(maps[i][-1] for i in range(self.total_column - 1)))
        for x in range(self.total_column - 1):
            if x in free:
                rep.append(x)
                t = []
                for j in range(self.total_column - 1):
                    t.append(maps[j][x])
                rep.append(tuple(t))
    
        ret_str = []
    
        ret_str.append("[" + "  ".join(str(x) for x in rep[0]) + "]")
        for i in range(1, len(rep), 2):
            ret_str.append(f"x{rep[i] + 1}[" + "  ".join(str(x) for x in rep[i + 1]) + "]")
        return " + ".join(ret_str)


    def interpret(self):
        # No Solution
        for row in self.SYSTEM:
            nz = (np.nonzero(row))[0]
            if len(nz) == 1 and nz[0] == self.total_row - 1:
                return 0
    
        pivots = self.find_pivots()
    
        # One Solution
        if len(pivots) == self.total_column - 1:
            return np.array([self.SYSTEM[i][-1] for i in range(self.total_row)])
    
        # Infinite Solutions
        return self.parameterize_infinite_solutions()
    
    def get_solution(self):
        interpretation = self.interpret()

        if isinstance(interpretation, int):
            return("System Inconsistent/No Solution.")
    
     
        else:
            f = "[" + "  ".join(f"x{i + 1}" for i in range(self.total_column - 1)) + "]"
            if isinstance(interpretation, str):
                return f + " = " + interpretation
            elif self.DTYPE is Fraction:
                return f + " = " + "[" + "  ".join(str(x) for x in interpretation) + "]"
            else:
                return f + " = " + interpretation
    def solve(self):
        self.ref()
        self.rref()
        print(self.get_solution())

        return

