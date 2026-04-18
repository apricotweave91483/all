from typing import List, Union, Optional, Tuple
from copy import deepcopy
import math


def _gcd(a: int, b: int) -> int:
    """Calculate greatest common divisor using Euclidean algorithm."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _simplify_expression(expr):
    """
    Simplify an expression. For Fractions, they already simplify themselves,
    so just return as-is.
    """
    if isinstance(expr, Fraction):
        return expr
    return expr


class Fraction:
    """
    Custom Fraction class for exact arithmetic.
    Supports numeric fractions only.
    """
    
    def __new__(cls, numerator=None, denominator=None):
        """
        Create a Fraction. Handles deepcopy/unpickling when numerator is None.
        """
        # Handle deepcopy/unpickling - numerator might be None
        if numerator is None:
            instance = super().__new__(cls)
            return instance
        
        # Create Fraction normally
        instance = super().__new__(cls)
        return instance
    
    def __init__(self, numerator, denominator=None):
        """
        Create a Fraction from numerator and denominator, or from a string/number.
        
        Examples:
            Fraction(1, 2)      # 1/2
            Fraction(3)         # 3/1
            Fraction("1/2")     # 1/2
            Fraction("1.5")     # 3/2
            Fraction(1.5)       # 3/2
        """
        if denominator is None:
            # Single argument - could be int, float, or string
            if isinstance(numerator, Fraction):
                self.num = numerator.num
                self.den = numerator.den
                return
            elif isinstance(numerator, str):
                # Parse string like "1/2", "3", "1.5"
                if '/' in numerator:
                    parts = numerator.split('/')
                    if len(parts) != 2:
                        raise ValueError(f"Invalid fraction string: {numerator}")
                    num_str, den_str = parts[0].strip(), parts[1].strip()
                    try:
                        num = int(num_str)
                        den = int(den_str)
                    except ValueError:
                        raise ValueError(f"Invalid fraction string: {numerator}")
                else:
                    # Try as float/int
                    try:
                        val = float(numerator)
                        num, den = self._float_to_fraction(val)
                    except ValueError:
                        raise ValueError(f"Invalid fraction string: {numerator}")
            elif isinstance(numerator, (int, float)):
                if isinstance(numerator, float):
                    num, den = self._float_to_fraction(numerator)
                else:
                    num, den = numerator, 1
            else:
                raise TypeError(f"Cannot create Fraction from {type(numerator).__name__}")
        else:
            # Two arguments: numerator and denominator
            # Both must be numeric - proceed with normal fraction creation
            try:
                num = int(numerator)
                den = int(denominator)
            except (ValueError, TypeError):
                # Try converting to float first
                num_float = float(numerator)
                den_float = float(denominator)
                num, den = self._float_to_fraction(num_float / den_float)
        
        # Normalize: ensure denominator is positive, reduce to lowest terms
        if den == 0:
            raise ZeroDivisionError("Fraction denominator cannot be zero")
        
        if den < 0:
            num, den = -num, -den
        
        # Reduce to lowest terms
        if isinstance(num, int) and isinstance(den, int):
            g = _gcd(num, den)
            self.num = num // g
            self.den = den // g
        else:
            # If one is Fraction, convert both to Fraction and simplify
            if isinstance(num, int):
                num = Fraction(num, 1)
            if isinstance(den, int):
                den = Fraction(1, den)
            # For Fraction components, store as-is for now
            self.num = num
            self.den = den
    
    @staticmethod
    def _float_to_fraction(val: float) -> tuple:
        """Convert float to (numerator, denominator) tuple."""
        if val == 0.0:
            return (0, 1)
        
        # Handle negative
        sign = -1 if val < 0 else 1
        val = abs(val)
        
        # Convert to fraction using tolerance-based approach
        # Try common denominators first for exact representation
        tolerance = 1e-10
        
        # Try common denominators first
        for den in [1, 2, 3, 4, 5, 6, 8, 10, 16, 32, 64, 100, 1000, 10000]:
            num = round(val * den)
            if abs(val - num / den) < tolerance:
                return (sign * num, den)
        
        # Fallback: use fixed precision (1,000,000 denominator) for more precision
        # This is a simplified version - for production, use a more robust method
        num = int(round(val * 1000000))
        den = 1000000
        g = _gcd(num, den)
        return (sign * (num // g), den // g)
    
    def __repr__(self):
        # Check if denominator is 1 (handle both int and Fraction cases)
        if isinstance(self.den, int) and self.den == 1:
            return f"Fraction({self.num!r})"
        if isinstance(self.den, Fraction) and self.den.num == 1 and self.den.den == 1:
            return f"Fraction({self.num!r})"
        return f"Fraction({self.num!r}, {self.den!r})"
    
    def __str__(self):
        # Check if denominator is 1 (handle both int and Fraction cases)
        if isinstance(self.den, int) and self.den == 1:
            return str(self.num)
        if isinstance(self.den, Fraction) and self.den.num == 1 and self.den.den == 1:
            return str(self.num)
        # For Fraction denominators, convert to string properly
        if isinstance(self.den, Fraction):
            return f"{self.num}/({self.den})"
        return f"{self.num}/{self.den}"
    
    def __float__(self):
        """Convert to float."""
        num_val = float(self.num) if isinstance(self.num, Fraction) else self.num
        den_val = float(self.den) if isinstance(self.den, Fraction) else self.den
        return num_val / den_val
    
    def __int__(self):
        """Convert to int (truncates)."""
        num_val = int(self.num) if isinstance(self.num, Fraction) else self.num
        den_val = int(self.den) if isinstance(self.den, Fraction) else self.den
        return num_val // den_val
    
    def __add__(self, other):
        """Addition."""
        if isinstance(other, Fraction):
            # (a/b) + (c/d) = (ad + bc) / bd
            num = self.num * other.den + other.num * self.den
            den = self.den * other.den
            return Fraction(num, den)
        elif isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return self + other_frac
        return NotImplemented
    
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        """Subtraction."""
        if isinstance(other, Fraction):
            # (a/b) - (c/d) = (ad - bc) / bd
            num = self.num * other.den - other.num * self.den
            den = self.den * other.den
            return Fraction(num, den)
        elif isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return self - other_frac
        return NotImplemented
    
    def __rsub__(self, other):
        """Right subtraction."""
        if isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return other_frac - self
        return NotImplemented
    
    def __mul__(self, other):
        """Multiplication."""
        if isinstance(other, Fraction):
            # (a/b) * (c/d) = ac / bd
            num = self.num * other.num
            den = self.den * other.den
            return Fraction(num, den)
        elif isinstance(other, (int, float)):
            other_frac = Fraction(other)
            num = self.num * other_frac.num
            den = self.den * other_frac.den
            return Fraction(num, den)
        return NotImplemented
    
    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __truediv__(self, other):
        """Division."""
        if isinstance(other, Fraction):
            # Check for zero division
            if other.num == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            # (a/b) / (c/d) = ad / bc
            num = self.num * other.den
            den = self.den * other.num
            return Fraction(num, den)
        elif isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            other_frac = Fraction(other)
            return self / other_frac
        return NotImplemented
    
    def __rtruediv__(self, other):
        """Right division."""
        if isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return other_frac / self
        return NotImplemented
    
    def __neg__(self):
        """Negation."""
        return Fraction(-self.num, self.den)
    
    def __abs__(self):
        """Absolute value."""
        return Fraction(abs(self.num), self.den)
    
    def __eq__(self, other):
        """Equality."""
        if isinstance(other, Fraction):
            return self.num == other.num and self.den == other.den
        elif isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return self.num == other_frac.num and self.den == other_frac.den
        return False
    
    def __ne__(self, other):
        """Inequality."""
        return not self.__eq__(other)
    
    def __lt__(self, other):
        """Less than."""
        if isinstance(other, Fraction):
            return self.num * other.den < other.num * self.den
        elif isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return self.num * other_frac.den < other_frac.num * self.den
        return NotImplemented
    
    def __le__(self, other):
        """Less than or equal."""
        return self.__eq__(other) or self.__lt__(other)
    
    def __gt__(self, other):
        """Greater than."""
        if isinstance(other, Fraction):
            return self.num * other.den > other.num * self.den
        elif isinstance(other, (int, float)):
            other_frac = Fraction(other)
            return self.num * other_frac.den > other_frac.num * self.den
        return NotImplemented
    
    def __ge__(self, other):
        """Greater than or equal."""
        return self.__eq__(other) or self.__gt__(other)
    
    def __hash__(self):
        """Hash for use in sets and dictionaries."""
        return hash((self.num, self.den))
    
    def __bool__(self):
        """Truthiness - zero is False, non-zero is True."""
        if isinstance(self.num, Fraction):
            return bool(self.num)
        return self.num != 0


class Vector:
    """Vector class using Fraction for exact arithmetic."""
    
    def __init__(self, components: List[Union[int, float, Fraction, str]]):
        """
        Initialize a vector from a list of components.
        All components are converted to Fraction.
        """
        processed = []
        for c in components:
            if isinstance(c, Fraction):
                processed.append(c)
            else:
                try:
                    processed.append(Fraction(str(c)))
                except (ValueError, ZeroDivisionError):
                    raise ValueError(f"Cannot convert {c} to Fraction")
        self.components = processed
        self.dimension = len(self.components)
    
    @classmethod
    def FS(cls, s: str):
        """
        Create a Vector from a string.
        Supports space-separated or comma-separated values.
        
        Examples:
            Vector.FS("1 2 3")
            Vector.FS("1, 2, 3")
            Vector.FS("1.5 2/3 4")
        """
        # Remove brackets if present
        s = s.strip().strip('[]')
        
        # Try comma-separated first
        if ',' in s:
            parts = [p.strip() for p in s.split(',')]
        else:
            # Space-separated
            parts = s.split()
        
        # Process parts - convert to Fraction
        processed = []
        for p in parts:
            if not p:
                continue
            try:
                processed.append(Fraction(p))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert '{p}' to Fraction")
        
        return cls(processed)
    
    def __repr__(self):
        # Format with column alignment
        str_components = [str(c) for c in self.components]
        # Find max width for each column (just one row for vector)
        max_width = max(len(s) for s in str_components) if str_components else 0
        # Right-align each component
        aligned = [s.rjust(max_width) for s in str_components]
        row_str = '[' + ', '.join(aligned) + ']'
        return f"Vector(\n  {row_str}\n)"
    
    def __str__(self):
        return f"[{', '.join(str(c) for c in self.components)}]"
    
    def __len__(self):
        return self.dimension
    
    def __getitem__(self, index):
        return self.components[index]
    
    def __setitem__(self, index, value):
        if isinstance(value, Fraction):
            self.components[index] = value
        else:
            try:
                self.components[index] = Fraction(str(value))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {value} to Fraction")
    
    def __eq__(self, other):
        if not isinstance(other, Vector):
            return False
        if self.dimension != other.dimension:
            return False
        return all(self.components[i] == other.components[i] for i in range(self.dimension))
    
    def __add__(self, other):
        """Vector addition."""
        if not isinstance(other, Vector):
            raise TypeError("Can only add Vector to Vector")
        if self.dimension != other.dimension:
            raise ValueError("Vectors must have same dimension for addition")
        return Vector([self.components[i] + other.components[i] for i in range(self.dimension)])
    
    def __sub__(self, other):
        """Vector subtraction."""
        if not isinstance(other, Vector):
            raise TypeError("Can only subtract Vector from Vector")
        if self.dimension != other.dimension:
            raise ValueError("Vectors must have same dimension for subtraction")
        return Vector([self.components[i] - other.components[i] for i in range(self.dimension)])
    
    def __mul__(self, scalar):
        """Scalar multiplication."""
        if not isinstance(scalar, Fraction):
            try:
                scalar = Fraction(str(scalar))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {scalar} to Fraction")
        return Vector([scalar * c for c in self.components])
    
    def __rmul__(self, scalar):
        """Right scalar multiplication."""
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar):
        """Scalar division."""
        if not isinstance(scalar, Fraction):
            try:
                scalar = Fraction(str(scalar))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {scalar} to Fraction")
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        return Vector([c / scalar for c in self.components])
    
    def __neg__(self):
        """Negation."""
        return Vector([-c for c in self.components])
    
    @staticmethod
    def _coerce_vector_like(
        value,
        context: str = "Operation",
    ) -> "Vector":
        """Convert Vector/list/tuple input to Vector for REPL-friendly APIs."""
        if isinstance(value, Vector):
            return value
        if isinstance(value, (list, tuple)):
            return Vector(list(value))
        raise TypeError(f"{context} requires a Vector or list/tuple")
    
    def dot(self, other):
        """Dot product."""
        other = Vector._coerce_vector_like(other, "Dot product")
        if self.dimension != other.dimension:
            raise ValueError("Vectors must have same dimension for dot product")
        return sum(self.components[i] * other.components[i] for i in range(self.dimension))
    
    def __matmul__(self, other):
        """Use @ for dot product in quick REPL calculations."""
        return self.dot(other)
    
    def cross(self, other: "Vector") -> "Vector":
        """
        Cross product of two 3D vectors.
        
        For vectors a = [a1, a2, a3] and b = [b1, b2, b3]:
            a x b = [a2*b3 - a3*b2, a3*b1 - a1*b3, a1*b2 - a2*b1]
        """
        other = Vector._coerce_vector_like(other, "Cross product")
        if self.dimension != 3 or other.dimension != 3:
            raise ValueError("Cross product is only defined for 3D vectors")
        
        a1, a2, a3 = self.components
        b1, b2, b3 = other.components
        
        return Vector([
            a2 * b3 - a3 * b2,
            a3 * b1 - a1 * b3,
            a1 * b2 - a2 * b1
        ])
    
    def project_onto(self, other: Union["Vector", List[Union[int, float, Fraction, str]], Tuple[Union[int, float, Fraction, str], ...]]) -> "Vector":
        """
        Project this vector onto another vector-like target.
        Accepts a Vector or a list/tuple of numeric values.
        
        The projection of v onto w is:
            proj_w(v) = ((v · w) / (w · w)) * w
        """
        other = Vector._coerce_vector_like(other, "Projection")
        if self.dimension != other.dimension:
            raise ValueError("Vectors must have same dimension for projection")
        
        denom = other.dot(other)
        if denom == 0:
            raise ValueError("Cannot project onto the zero vector")
        
        coeff = self.dot(other) / denom
        return coeff * other
    
    def magnitude(self):
        """Calculate magnitude (length) of vector."""
        import math
        sum_squares = sum(c * c for c in self.components)
        # Convert to float for sqrt (returns float, not Fraction)
        return math.sqrt(float(sum_squares))
    
    def normalize(self):
        """Return normalized (unit) vector."""
        mag = self.magnitude()
        if mag == 0:
            raise ValueError("Cannot normalize zero vector")
        # Convert magnitude to Fraction for division
        return self / Fraction(str(mag))

    def floats(self) -> Tuple[float, ...]:
        """Return vector components as a tuple of floats."""
        return tuple(float(c) for c in self.components)
    
    def copy(self):
        """Return a copy of the vector."""
        return Vector(self.components.copy())


class Matrix:
    """Matrix class using Fraction for exact arithmetic."""
    
    def __init__(self, rows: List[Union[List[Union[int, float, Fraction, str]], Vector]], rows_as_vectors: bool = False):
        """
        Initialize a matrix from a list of rows or vectors.
        
        Args:
            rows: List of rows (each row is a list) or list of Vectors
            rows_as_vectors: If True and rows contains Vectors, treat them as rows.
                            If False (default) and rows contains Vectors, treat them as columns (mathematical convention).
                            Ignored if rows contains lists (always treated as rows).
        
        Examples:
            # List of lists (always rows)
            Matrix([[1, 2], [3, 4]])
            
            # List of Vectors (default: as columns)
            Matrix([v1, v2])  # v1 and v2 are columns
            
            # List of Vectors (explicit: as rows)
            Matrix([v1, v2], rows_as_vectors=True)  # v1 and v2 are rows
        """
        if not rows:
            raise ValueError("Matrix must have at least one row")
        
        # Check if input is list of Vectors
        is_vector_list = all(isinstance(row, Vector) for row in rows)
        
        if is_vector_list:
            # Input is list of Vectors
            vectors = rows
            if rows_as_vectors:
                # Treat vectors as rows
                processed_rows = [v.components for v in vectors]
            else:
                # Treat vectors as columns (mathematical convention)
                # Transpose: each vector becomes a column
                if not vectors:
                    raise ValueError("Matrix must have at least one vector")
                dim = vectors[0].dimension
                for v in vectors:
                    if v.dimension != dim:
                        raise ValueError("All vectors must have the same dimension")
                # Create rows by taking i-th component from each vector
                processed_rows = [[v.components[i] for v in vectors] for i in range(dim)]
        else:
            # Input is list of lists (traditional format)
            processed_rows = []
            for row in rows:
                processed_row = []
                for val in row:
                    if isinstance(val, Fraction):
                        processed_row.append(val)
                    else:
                        try:
                            processed_row.append(Fraction(str(val)))
                        except (ValueError, ZeroDivisionError):
                            raise ValueError(f"Cannot convert {val} to Fraction")
                processed_rows.append(processed_row)
        
        self.rows = processed_rows
        
        # Validate all rows have same length
        num_cols = len(self.rows[0])
        for i, row in enumerate(self.rows):
            if len(row) != num_cols:
                raise ValueError(f"Row {i} has inconsistent length")
        
        self.num_rows = len(self.rows)
        self.num_cols = num_cols
        
        # Create vector representation for rows
        self._row_vectors = [Vector(row) for row in self.rows]
        # Columns will be computed on demand (lazy evaluation)
        self._column_vectors = None
    
    @property
    def row_vectors(self):
        """Get rows as Vector objects."""
        return self._row_vectors
    
    @property
    def column_vectors(self):
        """Get columns as Vector objects."""
        if self._column_vectors is None:
            self._column_vectors = [
                Vector([self.rows[i][j] for i in range(self.num_rows)])
                for j in range(self.num_cols)
            ]
        return self._column_vectors
    
    def get_row(self, index):
        """Get row at index as Vector."""
        return self._row_vectors[index]
    
    def get_column(self, index):
        """Get column at index as Vector."""
        return self.column_vectors[index]
    
    def _invalidate_column_cache(self):
        """Invalidate column cache when rows are modified."""
        self._column_vectors = None
    
    @classmethod
    def FS(cls, s: str):
        """
        Create a Matrix from a string.
        Supports multiple formats:
        
        1. Multi-line with row count first:
           "3\n1 2 3\n4 5 6\n7 8 9"
        
        2. Multi-line without row count:
           "1 2 3\n4 5 6\n7 8 9"
        
        3. Python list syntax:
           "[[1, 2, 3], [4, 5, 6], [7, 8, 9]]"
        
        4. Space-separated rows (one per line):
           "1 2 3\n4 5 6"
        
        Examples:
            Matrix.FS("2\n1 2\n3 4")
            Matrix.FS("1 2 3\\n4 5 6")
            Matrix.FS("[[1,2],[3,4]]")
        """
        s = s.strip()
        
        # Try Python list syntax first
        if s.startswith('[') and '],' in s:
            import ast
            try:
                rows = ast.literal_eval(s)
                return cls(rows)
            except:
                pass
        
        # Split by newlines
        lines = [line.strip() for line in s.split('\n') if line.strip()]
        
        if not lines:
            raise ValueError("Empty matrix input")
        
        # Check if first line is just a number (row count)
        try:
            row_count = int(lines[0])
            if len(lines) == row_count + 1:
                # Format: number of rows, then rows
                lines = lines[1:]
        except ValueError:
            # First line is not a number, treat all lines as rows
            pass
        
        # Parse each line as space-separated or comma-separated values
        rows = []
        for line in lines:
            # Remove brackets if present
            line = line.strip().strip('[]')
            
            # Try comma-separated first
            if ',' in line:
                parts = [p.strip() for p in line.split(',')]
            else:
                # Space-separated
                parts = line.split()
            
            # Process parts - convert to Fraction
            processed_parts = []
            for p in parts:
                if not p:
                    continue
                try:
                    processed_parts.append(Fraction(p))
                except (ValueError, ZeroDivisionError):
                    raise ValueError(f"Cannot convert '{p}' to Fraction")
            
            if processed_parts:
                rows.append(processed_parts)
        
        if not rows:
            raise ValueError("No valid rows found")
        
        return cls(rows)
    
    @classmethod
    def FI(cls, prompt: str = None):
        """
        Interactive input for Matrix in REPL.
        Prompts user to enter rows one by one.
        
        Usage:
            M = Matrix.FI()
            # Enter rows when prompted, empty line to finish
        """
        if prompt:
            print(prompt)
        
        print("Enter matrix rows (space or comma separated). Empty line to finish:")
        rows = []
        
        while True:
            try:
                line = input().strip()
                if not line:
                    break
                
                # Parse the line
                line = line.strip().strip('[]')
                if ',' in line:
                    parts = [p.strip() for p in line.split(',')]
                else:
                    parts = line.split()
                
                # Process parts - convert to Fraction
                processed_parts = []
                for p in parts:
                    if not p:
                        continue
                    try:
                        processed_parts.append(Fraction(p))
                    except (ValueError, ZeroDivisionError):
                        raise ValueError(f"Cannot convert '{p}' to Fraction")
                
                if processed_parts:
                    rows.append(processed_parts)
            except (EOFError, KeyboardInterrupt):
                break
        
        if not rows:
            raise ValueError("No rows entered")
        
        return cls(rows)
    
    def __repr__(self):
        # Format with column alignment
        # Convert all to strings
        str_rows = [[str(c) for c in row] for row in self.rows]
        # Find max width for each column
        max_widths = []
        for col_idx in range(self.num_cols):
            max_width = max(len(str_rows[row_idx][col_idx]) 
                          for row_idx in range(self.num_rows))
            max_widths.append(max_width)
        # Right-align each column
        aligned_rows = []
        for row in str_rows:
            aligned_row = [row[col_idx].rjust(max_widths[col_idx]) 
                          for col_idx in range(self.num_cols)]
            row_str = '[' + ', '.join(aligned_row) + ']'
            aligned_rows.append(f"  {row_str}")
        return f"Matrix(\n" + '\n'.join(aligned_rows) + "\n)"
    
    def __str__(self):
        return '\n'.join('[' + ', '.join(str(c) for c in row) + ']' for row in self.rows)
    
    def __eq__(self, other):
        if not isinstance(other, Matrix):
            return False
        if self.num_rows != other.num_rows or self.num_cols != other.num_cols:
            return False
        return all(self.rows[i] == other.rows[i] for i in range(self.num_rows))
    
    def __getitem__(self, index):
        """Get row by index."""
        return self._row_vectors[index]
    
    def __setitem__(self, index, value):
        """Set row by index."""
        if isinstance(value, Vector):
            if len(value) != self.num_cols:
                raise ValueError("Vector dimension must match matrix column count")
            self._row_vectors[index] = value
            self.rows[index] = value.components
            self._invalidate_column_cache()
        else:
            raise TypeError("Must assign Vector to matrix row")
    
    def get(self, row, col):
        """Get element at (row, col)."""
        return self.rows[row][col]
    
    def set(self, row, col, value):
        """Set element at (row, col)."""
        if isinstance(value, Fraction):
            self.rows[row][col] = value
        else:
            try:
                self.rows[row][col] = Fraction(str(value))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {value} to Fraction")
        self._row_vectors[row][col] = self.rows[row][col]
        self._invalidate_column_cache()
    
    def copy(self):
        """Return a deep copy of the matrix."""
        return Matrix(deepcopy(self.rows))
    
    def transpose(self):
        """Return transpose of matrix."""
        return Matrix([[self.rows[j][i] for j in range(self.num_rows)] 
                       for i in range(self.num_cols)])
    
    def __add__(self, other):
        """Matrix addition."""
        if not isinstance(other, Matrix):
            raise TypeError("Can only add Matrix to Matrix")
        if self.num_rows != other.num_rows or self.num_cols != other.num_cols:
            raise ValueError("Matrices must have same dimensions for addition")
        return Matrix([[self.rows[i][j] + other.rows[i][j] 
                       for j in range(self.num_cols)] 
                       for i in range(self.num_rows)])
    
    def __sub__(self, other):
        """Matrix subtraction."""
        if not isinstance(other, Matrix):
            raise TypeError("Can only subtract Matrix from Matrix")
        if self.num_rows != other.num_rows or self.num_cols != other.num_cols:
            raise ValueError("Matrices must have same dimensions for subtraction")
        return Matrix([[self.rows[i][j] - other.rows[i][j] 
                       for j in range(self.num_cols)] 
                       for i in range(self.num_rows)])
    
    def __mul__(self, other):
        """Matrix multiplication or scalar multiplication."""
        if isinstance(other, (list, tuple)):
            other = Vector(list(other))
        
        if isinstance(other, (int, float, Fraction)):
            # Scalar multiplication
            if not isinstance(other, Fraction):
                try:
                    scalar = Fraction(str(other))
                except (ValueError, ZeroDivisionError):
                    raise ValueError(f"Cannot convert {other} to Fraction")
            else:
                scalar = other
            return Matrix([[scalar * self.rows[i][j] 
                           for j in range(self.num_cols)] 
                           for i in range(self.num_rows)])
        elif isinstance(other, Matrix):
            # Matrix multiplication
            if self.num_cols != other.num_rows:
                raise ValueError("Matrix dimensions incompatible for multiplication")
            result = []
            for i in range(self.num_rows):
                row = []
                for j in range(other.num_cols):
                    val = sum(self.rows[i][k] * other.rows[k][j] 
                             for k in range(self.num_cols))
                    row.append(val)
                result.append(row)
            return Matrix(result)
        elif isinstance(other, Vector):
            # Matrix-vector multiplication
            if self.num_cols != other.dimension:
                raise ValueError("Matrix columns must match vector dimension")
            result = []
            for i in range(self.num_rows):
                val = sum(self.rows[i][j] * other.components[j] 
                         for j in range(self.num_cols))
                result.append(val)
            return Vector(result)
        else:
            raise TypeError("Can only multiply Matrix by scalar, Matrix, or Vector")
    
    def __matmul__(self, other):
        """Use @ as alias for matrix multiplication in REPL."""
        return self.__mul__(other)
    
    def __rmul__(self, scalar):
        """Right scalar multiplication."""
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar):
        """Scalar division."""
        if not isinstance(scalar, Fraction):
            try:
                scalar = Fraction(str(scalar))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {scalar} to Fraction")
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        return self * (Fraction(1) / scalar)

    def __pow__(self, exponent, modulo=None):
        """
        Matrix exponentiation for integer powers.
        Supports negative powers via matrix inverse.
        """
        if modulo is not None:
            raise TypeError("Modulo is not supported for Matrix exponentiation")
        if not isinstance(exponent, int):
            raise TypeError("Matrix exponent must be an integer")
        if self.num_rows != self.num_cols:
            raise ValueError("Matrix exponentiation is only defined for square matrices")

        # Identity matrix for exponent 0 and iterative accumulation.
        identity = Matrix([
            [Fraction(1) if i == j else Fraction(0) for j in range(self.num_cols)]
            for i in range(self.num_rows)
        ])

        if exponent == 0:
            return identity
        if exponent < 0:
            return (self.inverse()) ** (-exponent)

        # Exponentiation by squaring for efficiency.
        result = identity
        base = self.copy()
        n = exponent

        while n > 0:
            if n % 2 == 1:
                result = result * base
            n //= 2
            if n > 0:
                base = base * base

        return result
    
    # Elementary Row Operations
    def swap_rows(self, i, j):
        """Swap rows i and j."""
        if i < 0 or i >= self.num_rows or j < 0 or j >= self.num_rows:
            raise IndexError("Row index out of range")
        self.rows[i], self.rows[j] = self.rows[j], self.rows[i]
        self._row_vectors[i], self._row_vectors[j] = self._row_vectors[j], self._row_vectors[i]
        self._invalidate_column_cache()
    
    def scale_row(self, i, scalar):
        """Multiply row i by scalar."""
        if i < 0 or i >= self.num_rows:
            raise IndexError("Row index out of range")
        # Convert scalar to Fraction if needed
        if not isinstance(scalar, Fraction):
            try:
                scalar = Fraction(str(scalar))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {scalar} to Fraction")
        # Multiply and simplify each element
        self.rows[i] = [_simplify_expression(scalar * val) for val in self.rows[i]]
        self._row_vectors[i] = _simplify_expression(self._row_vectors[i] * scalar)
        self._invalidate_column_cache()
    
    def add_row_multiple(self, i, j, scalar):
        """Add scalar * row j to row i."""
        if i < 0 or i >= self.num_rows or j < 0 or j >= self.num_rows:
            raise IndexError("Row index out of range")
        # Convert scalar to Fraction if needed
        if not isinstance(scalar, Fraction):
            try:
                scalar = Fraction(str(scalar))
            except (ValueError, ZeroDivisionError):
                raise ValueError(f"Cannot convert {scalar} to Fraction")
        # Add and simplify each element
        self.rows[i] = [_simplify_expression(self.rows[i][k] + scalar * self.rows[j][k])
                       for k in range(self.num_cols)]
        self._row_vectors[i] = _simplify_expression(self._row_vectors[i] + scalar * self._row_vectors[j])
        self._invalidate_column_cache()
    
    def ref(self):
        """Return Row Echelon Form (REF) of matrix."""
        result = self.copy()
        pivot_row = 0
        
        for col in range(result.num_cols):
            # Find pivot
            pivot_found = False
            for row in range(pivot_row, result.num_rows):
                if result.rows[row][col] != 0:
                    if row != pivot_row:
                        result.swap_rows(pivot_row, row)
                    pivot_found = True
                    break
            
            if not pivot_found:
                continue
            
            # Make pivot 1 (optional, but helpful)
            pivot_val = result.rows[pivot_row][col]
            if pivot_val != 1 and pivot_val != 0:
                result.scale_row(pivot_row, Fraction(1) / pivot_val)
            
            # Eliminate below pivot
            for row in range(pivot_row + 1, result.num_rows):
                if result.rows[row][col] != 0:
                    factor = -result.rows[row][col] / result.rows[pivot_row][col]
                    result.add_row_multiple(row, pivot_row, factor)
            
            pivot_row += 1
            if pivot_row >= result.num_rows:
                break
        
        return result
    
    def rref(self):
        """Return Reduced Row Echelon Form (RREF) of matrix."""
        result = self.ref()
        
        # Find pivot positions
        pivots = []
        pivot_row = 0
        for col in range(result.num_cols):
            if pivot_row < result.num_rows and result.rows[pivot_row][col] != 0:
                pivots.append((pivot_row, col))
                pivot_row += 1
        
        # Back substitution
        for pivot_row, pivot_col in reversed(pivots):
            # Eliminate above pivot
            pivot_val = result.rows[pivot_row][pivot_col]
            for row in range(pivot_row - 1, -1, -1):
                if result.rows[row][pivot_col] != 0:
                    # Factor should eliminate the coefficient: factor * pivot_val + coeff = 0
                    # So factor = -coeff / pivot_val
                    factor = -result.rows[row][pivot_col] / pivot_val
                    result.add_row_multiple(row, pivot_row, factor)
        
        return result
    
    def determinant(self):
        """Calculate determinant using cofactor expansion."""
        if self.num_rows != self.num_cols:
            raise ValueError("Determinant only defined for square matrices")
        
        if self.num_rows == 1:
            return self.rows[0][0]
        
        if self.num_rows == 2:
            return self.rows[0][0] * self.rows[1][1] - self.rows[0][1] * self.rows[1][0]
        
        # Use first row for cofactor expansion
        det = Fraction(0)
        for j in range(self.num_cols):
            # Create minor matrix
            minor_rows = []
            for i in range(1, self.num_rows):
                minor_rows.append([self.rows[i][k] for k in range(self.num_cols) if k != j])
            minor = Matrix(minor_rows)
            
            cofactor = (-1) ** j * self.rows[0][j] * minor.determinant()
            det += cofactor
        
        return det
    
    def inverse(self):
        """Calculate inverse matrix using Gauss-Jordan elimination."""
        if self.num_rows != self.num_cols:
            raise ValueError("Inverse only defined for square matrices")
        
        det = self.determinant()
        if det == 0:
            raise ValueError("Matrix is singular (determinant is zero)")
        
        # Create augmented matrix [A | I]
        augmented_rows = []
        for i in range(self.num_rows):
            row = self.rows[i].copy()
            row.extend([Fraction(1) if j == i else Fraction(0) 
                       for j in range(self.num_rows)])
            augmented_rows.append(row)
        
        augmented = Matrix(augmented_rows)
        rref = augmented.rref()
        
        # Extract inverse from right half
        inverse_rows = []
        for i in range(self.num_rows):
            inverse_rows.append([rref.rows[i][j] for j in range(self.num_rows, rref.num_cols)])
        
        return Matrix(inverse_rows)
    
    def rank(self):
        """Calculate rank of matrix."""
        ref_matrix = self.ref()
        rank = 0
        for row in ref_matrix.rows:
            if any(val != 0 for val in row):
                rank += 1
        return rank


class System:
    """System of linear equations represented as an augmented matrix."""
    
    @staticmethod
    def _build_augmented_matrix(
        coeff_matrix: Matrix,
        rhs: Union[
            Vector,
            List[Union[int, float, Fraction, str]],
            Tuple[Union[int, float, Fraction, str], ...],
        ],
    ) -> Matrix:
        """Build [A | b] from coefficient matrix A and right-hand-side vector b."""
        if not isinstance(coeff_matrix, Matrix):
            raise TypeError("Coefficient input must be a Matrix")
        
        if isinstance(rhs, Vector):
            rhs_vector = rhs
        elif isinstance(rhs, (list, tuple)):
            rhs_vector = Vector(list(rhs))
        else:
            raise TypeError("RHS must be a Vector or list/tuple")
        
        if coeff_matrix.num_rows != rhs_vector.dimension:
            raise ValueError("RHS vector dimension must match number of matrix rows")
        
        augmented_rows = [
            coeff_matrix.rows[i].copy() + [rhs_vector.components[i]]
            for i in range(coeff_matrix.num_rows)
        ]
        return Matrix(augmented_rows)
    
    def __init__(self, matrix):
        """
        Initialize system from:
        - an augmented matrix [A | b]
        - a list of column vectors (last column is b)
        - a pair (A, b) or [A, b], where A is coefficient Matrix and b is RHS vector/list
        
        Last column is interpreted as the constants (right-hand side).
        
        Args:
            matrix: Matrix, list of column Vectors, or (A, b)/[A, b].
        
        Examples:
            # From Matrix
            S = System(Matrix([[1, 2, 5], [3, 4, 11]]))
            
            # From list of column vectors
            v = Vector([1, 2])
            w = Vector([2, 1])
            x = Vector([4, 5])
            S = System([v, w, x])
            
            # From coefficient matrix A and RHS b
            A = Matrix([[1, 2], [3, 4]])
            b = Vector([5, 11])
            S = System((A, b))
        """
        # (A, b) or [A, b]
        if isinstance(matrix, (tuple, list)) and len(matrix) == 2 and isinstance(matrix[0], Matrix):
            matrix = System._build_augmented_matrix(matrix[0], matrix[1])
        # List of column vectors (old behavior)
        elif isinstance(matrix, list) and all(isinstance(v, Vector) for v in matrix):
            matrix = Matrix(matrix)  # Vectors treated as columns by default
        
        if not isinstance(matrix, Matrix):
            raise TypeError(
                "System expects an augmented Matrix, a list of column Vectors, or (A, b)/[A, b]"
            )
        
        if matrix.num_cols < 2:
            raise ValueError("Augmented matrix must have at least 2 columns")
        self.matrix = matrix.copy()
        self.num_equations = matrix.num_rows
        self.num_variables = matrix.num_cols - 1
    
    @classmethod
    def from_coefficients(
        cls,
        coeff_matrix: Matrix,
        rhs: Union[
            Vector,
            List[Union[int, float, Fraction, str]],
            Tuple[Union[int, float, Fraction, str], ...],
        ],
    ):
        """
        Create a System from coefficient matrix A and RHS vector b.
        
        Examples:
            A = Matrix([[1, 2], [3, 4]])
            b = Vector([5, 11])
            S = System.from_coefficients(A, b)
        """
        return cls(cls._build_augmented_matrix(coeff_matrix, rhs))
    
    @classmethod
    def FS(cls, s: str):
        """
        Create a System from a string (same format as Matrix.FS).
        Last column is interpreted as constants.
        
        Examples:
            System.FS("2\\n1 2 5\\n3 4 11")
            System.FS("1 2 5\\n3 4 11")
        """
        matrix = Matrix.FS(s)
        return cls(matrix)
    
    @classmethod
    def FI(cls, prompt: str = None):
        """
        Interactive input for System in REPL.
        Prompts user to enter augmented matrix rows.
        
        Usage:
            S = System.FI()
            # Enter rows when prompted, empty line to finish
        """
        matrix = Matrix.FI(prompt)
        return cls(matrix)
    
    def solution(self):
        """
        Solve the system of linear equations.
        Returns a dictionary with:
        - 'type': 'no_solution', 'unique', or 'infinite'
        - 'solution': solution vector (if unique) or parameterization (if infinite)
        """
        rref = self.matrix.rref()
        
        # Check for inconsistency (row like [0, 0, ..., 0, |, non-zero])
        for i in range(rref.num_rows):
            # Check if all coefficients are zero but constant is non-zero
            all_zero = all(rref.rows[i][j] == 0 for j in range(self.num_variables))
            constant = rref.rows[i][self.num_variables]
            if all_zero and constant != 0:
                return {
                    'type': 'no_solution',
                    'solution': None,
                    'message': 'No solution - system is inconsistent'
                }
        
        # Find pivot positions
        pivots = []
        pivot_row = 0
        for col in range(self.num_variables):
            if pivot_row < rref.num_rows and rref.rows[pivot_row][col] != 0:
                pivots.append((pivot_row, col))
                pivot_row += 1
        
        # Check if we have unique solution
        if len(pivots) == self.num_variables:
            # Unique solution
            solution = []
            for var_idx in range(self.num_variables):
                # Find pivot for this variable
                pivot_found = False
                for pr, pc in pivots:
                    if pc == var_idx:
                        sol_val = rref.rows[pr][self.num_variables]
                        # Simplify the solution value
                        sol_val = _simplify_expression(sol_val)
                        solution.append(sol_val)
                        pivot_found = True
                        break
                if not pivot_found:
                    solution.append(Fraction(0))
            
            return {
                'type': 'unique',
                'solution': Vector(solution),
                'message': f'Unique solution: {Vector(solution)}'
            }
        
        # Infinite solutions - parameterize
        free_vars = []
        basic_vars = [False] * self.num_variables
        
        for pr, pc in pivots:
            basic_vars[pc] = True
        
        for i in range(self.num_variables):
            if not basic_vars[i]:
                free_vars.append(i)
        
        # Build parameterization
        param_solution = {}
        param_solution['free_variables'] = free_vars
        param_solution['basic_variables'] = [i for i in range(self.num_variables) if basic_vars[i]]
        
        # For each basic variable, express in terms of free variables
        expressions = {}
        for pr, pc in pivots:
            # Variable pc = constant + sum of free variable terms
            constant = rref.rows[pr][self.num_variables]
            # Simplify constant
            constant = _simplify_expression(constant)
            terms = {}
            for fv in free_vars:
                coeff = rref.rows[pr][fv]
                if coeff != 0:
                    # Simplify the coefficient
                    simplified_coeff = _simplify_expression(-coeff)  # Negative because we move to other side
                    # Only add if not zero after simplification
                    if simplified_coeff != 0 and simplified_coeff != Fraction(0):
                        terms[fv] = simplified_coeff
            expressions[pc] = {'constant': constant, 'terms': terms}
        
        # For free variables, they are themselves
        for fv in free_vars:
            expressions[fv] = {'constant': Fraction(0), 'terms': {fv: Fraction(1)}}
        
        param_solution['expressions'] = expressions
        
        return {
            'type': 'infinite',
            'solution': param_solution,
            'message': f'Infinite solutions with {len(free_vars)} free variable(s)'
        }
    
    def solve(self):
        """
        Solve the system and print the result nicely.
        """
        result = self.solution()
        
        if result['type'] == 'no_solution':
            print("No solution - system is inconsistent")
        
        elif result['type'] == 'unique':
            sol = result['solution']
            print("Unique solution:")
            # Format as [x1, x2, ...] = [values] with nice fraction display
            var_names = ', '.join(f"x{i+1}" for i in range(self.num_variables))
            sol_str = '[' + ', '.join(str(c) for c in sol.components) + ']'
            print(f"  [{var_names}] = {sol_str}")
        
        elif result['type'] == 'infinite':
            param = result['solution']
            free_vars = param['free_variables']
            expressions = param['expressions']
            
            print(f"Infinite solutions with {len(free_vars)} free variable(s):")
            print()
            
            # Print each variable's expression
            for var_idx in range(self.num_variables):
                expr = expressions[var_idx]
                var_name = f"x{var_idx + 1}"
                
                # Build the expression string
                parts = []
                
                # Constant term
                const = expr['constant']
                if const != 0:
                    parts.append(str(const))
                elif not expr['terms']:
                    parts.append("0")
                
                # Terms with free variables
                for fv, coeff in sorted(expr['terms'].items()):
                    if coeff != 0:
                        coeff_str = str(coeff)
                        if coeff == 1:
                            term_str = f"t{fv + 1}"
                        elif coeff == -1:
                            term_str = f"-t{fv + 1}"
                        else:
                            term_str = f"{coeff_str}*t{fv + 1}"
                        parts.append(term_str)
                
                if not parts:
                    parts.append("0")
                
                expr_str = " + ".join(parts).replace(" + -", " - ")
                print(f"  {var_name} = {expr_str}")
    
    def __repr__(self):
        # Format System with matrix aligned, same format as Matrix
        # Convert all to strings
        str_rows = [[str(c) for c in row] for row in self.matrix.rows]
        # Find max width for each column
        max_widths = []
        for col_idx in range(self.matrix.num_cols):
            max_width = max(len(str_rows[row_idx][col_idx]) 
                          for row_idx in range(self.matrix.num_rows))
            max_widths.append(max_width)
        # Right-align each column
        aligned_rows = []
        for row in str_rows:
            aligned_row = [row[col_idx].rjust(max_widths[col_idx]) 
                          for col_idx in range(self.matrix.num_cols)]
            row_str = '[' + ', '.join(aligned_row) + ']'
            aligned_rows.append(f"  {row_str}")
        return f"System(\n" + '\n'.join(aligned_rows) + "\n)"
    
    def __str__(self):
        result = "System of Linear Equations:\n"
        result += str(self.matrix)
        return result


class Ops:
    """Linear Algebra Operations - utility class for operations on vectors and matrices."""
    
    @staticmethod
    def gram_schmidt(vectors: Union[List[Vector], Matrix], use_columns: bool = True) -> List[Vector]:
        """
        Apply Gram-Schmidt orthogonalization to a list of vectors or matrix columns/rows.
        Returns an orthonormal basis spanning the same subspace.
        
        Args:
            vectors: Either a list of Vector objects or a Matrix
            use_columns: If vectors is a Matrix, True uses columns, False uses rows.
                        Ignored if vectors is a List[Vector].
        
        Example:
            # With list of vectors
            v1 = Vector([1, 1, 0])
            v2 = Vector([1, 0, 1])
            orthonormal = Ops.gram_schmidt([v1, v2])
            
            # With matrix (uses columns by default)
            A = Matrix([[1, 1], [1, 0], [0, 1]])
            orthonormal = Ops.gram_schmidt(A)  # Orthonormalize columns
            orthonormal = Ops.gram_schmidt(A, use_columns=False)  # Orthonormalize rows
        """
        # Handle Matrix input
        if isinstance(vectors, Matrix):
            if use_columns:
                vectors = vectors.column_vectors
            else:
                vectors = vectors.row_vectors
        
        if not vectors:
            return []
        
        # Check all vectors have same dimension
        dim = vectors[0].dimension
        for v in vectors:
            if v.dimension != dim:
                raise ValueError("All vectors must have the same dimension")
        
        orthogonal = []
        
        for v in vectors:
            # Start with the original vector
            u = v.copy()
            
            # Subtract projection onto each previous orthogonal vector
            for prev_u in orthogonal:
                # Project v onto prev_u
                projection = (v.dot(prev_u) / prev_u.dot(prev_u)) * prev_u
                u = u - projection
            
            # Only add if not zero vector
            if any(c != 0 for c in u.components):
                # Normalize
                try:
                    u = u.normalize()
                except ValueError:  # Zero vector
                    continue
                orthogonal.append(u)
        
        return orthogonal
    
    @staticmethod
    def null_space(matrix: Matrix) -> List[Vector]:
        """
        Find a basis for the null space (kernel) of a matrix.
        Returns list of vectors that span the null space.
        
        Example:
            A = Matrix([[1, 2], [2, 4]])
            null_basis = Ops.null_space(A)
        """
        # Solve Ax = 0 by finding RREF of augmented matrix [A | 0]
        augmented_rows = []
        for row in matrix.rows:
            augmented_rows.append(row + [Fraction(0)])
        
        augmented = Matrix(augmented_rows)
        rref = augmented.rref()
        
        # Find free variables (columns without pivots)
        pivots = []
        pivot_row = 0
        for col in range(matrix.num_cols):
            if pivot_row < rref.num_rows and rref.rows[pivot_row][col] != 0:
                pivots.append((pivot_row, col))
                pivot_row += 1
        
        pivot_cols = {pc for _, pc in pivots}
        free_vars = [i for i in range(matrix.num_cols) if i not in pivot_cols]
        
        if not free_vars:
            return []  # Trivial null space
        
        # For each free variable, create a null space vector
        null_vectors = []
        for fv in free_vars:
            # Create vector where free variable = 1, others determined by RREF
            null_vec = [Fraction(0)] * matrix.num_cols
            null_vec[fv] = Fraction(1)
            
            # Back-substitute to find values of basic variables
            for pr, pc in reversed(pivots):
                # Variable pc = -sum of free variable terms
                value = Fraction(0)
                for fv_idx in free_vars:
                    if fv_idx < matrix.num_cols:
                        coeff = rref.rows[pr][fv_idx]
                        value -= coeff * null_vec[fv_idx]
                null_vec[pc] = value
            
            null_vectors.append(Vector(null_vec))
        
        return null_vectors
    
    @staticmethod
    def column_space(matrix: Matrix) -> List[Vector]:
        """
        Find a basis for the column space of a matrix.
        Returns list of linearly independent column vectors.
        
        Example:
            A = Matrix([[1, 2, 3], [4, 5, 6]])
            col_basis = Ops.column_space(A)
        """
        rref = matrix.rref()
        
        # Find pivot columns
        pivots = []
        pivot_row = 0
        for col in range(rref.num_cols):
            if pivot_row < rref.num_rows and rref.rows[pivot_row][col] != 0:
                pivots.append((pivot_row, col))
                pivot_row += 1
        
        # Return original columns (not RREF columns) corresponding to pivots
        pivot_cols = [pc for _, pc in pivots]
        return [matrix.get_column(pc) for pc in pivot_cols]
    
    @staticmethod
    def row_space(matrix: Matrix) -> List[Vector]:
        """
        Find a basis for the row space of a matrix.
        Returns list of linearly independent row vectors.
        
        Example:
            A = Matrix([[1, 2, 3], [4, 5, 6]])
            row_basis = Ops.row_space(A)
        """
        rref = matrix.rref()
        
        # Non-zero rows in RREF form a basis for row space
        basis = []
        for row in rref.row_vectors:
            if any(c != 0 for c in row.components):
                basis.append(row)
        
        return basis
    
    @staticmethod
    def is_linearly_independent(vectors: Union[List[Vector], Matrix], check_columns: bool = True) -> bool:
        """
        Check if a list of vectors or matrix columns/rows are linearly independent.
        
        Args:
            vectors: Either a list of Vector objects or a Matrix
            check_columns: If vectors is a Matrix, True checks columns, False checks rows.
                          Ignored if vectors is a List[Vector].
        
        Example:
            # With list of vectors
            v1 = Vector([1, 0])
            v2 = Vector([0, 1])
            Ops.is_linearly_independent([v1, v2])  # True
            
            # With matrix (checks columns by default)
            A = Matrix([[1, 2], [3, 4]])
            Ops.is_linearly_independent(A)  # True (columns are independent)
            Ops.is_linearly_independent(A, check_columns=False)  # Check rows instead
        """
        # Handle Matrix input
        if isinstance(vectors, Matrix):
            if check_columns:
                vectors = vectors.column_vectors
            else:
                vectors = vectors.row_vectors
        
        if not vectors:
            return True
        
        # Check all vectors have same dimension
        dim = vectors[0].dimension
        for v in vectors:
            if v.dimension != dim:
                raise ValueError("All vectors must have the same dimension")
        
        # Create matrix with vectors as columns
        if len(vectors) > dim:
            return False  # More vectors than dimension means dependent
        
        matrix_rows = []
        for i in range(dim):
            row = [v.components[i] for v in vectors]
            matrix_rows.append(row)
        
        matrix = Matrix(matrix_rows)
        rank = matrix.rank()
        
        return rank == len(vectors)
    
    @staticmethod
    def span(vectors: Union[List[Vector], Matrix], use_columns: bool = True) -> List[Vector]:
        """
        Find a basis for the span of a list of vectors or matrix columns/rows.
        Returns linearly independent vectors that span the same space.
        
        Args:
            vectors: Either a list of Vector objects or a Matrix
            use_columns: If vectors is a Matrix, True uses columns, False uses rows.
                        Ignored if vectors is a List[Vector].
        
        Example:
            # With list of vectors
            v1 = Vector([1, 0, 0])
            v2 = Vector([0, 1, 0])
            v3 = Vector([1, 1, 0])
            basis = Ops.span([v1, v2, v3])  # Returns basis for xy-plane
            
            # With matrix (uses columns by default)
            A = Matrix([[1, 0, 1], [0, 1, 1], [0, 0, 0]])
            basis = Ops.span(A)  # Basis for column space
            basis = Ops.span(A, use_columns=False)  # Basis for row space
        """
        # Handle Matrix input
        if isinstance(vectors, Matrix):
            if use_columns:
                return Ops.column_space(vectors)
            else:
                return Ops.row_space(vectors)
        
        if not vectors:
            return []
        
        # Check all vectors have same dimension
        dim = vectors[0].dimension
        for v in vectors:
            if v.dimension != dim:
                raise ValueError("All vectors must have the same dimension")
        
        # Create matrix with vectors as columns
        matrix_rows = []
        for i in range(dim):
            row = [v.components[i] for v in vectors]
            matrix_rows.append(row)
        
        matrix = Matrix(matrix_rows)
        # Column space gives basis for span
        return Ops.column_space(matrix)
    
    @staticmethod
    def project_onto_subspace(vector: Vector, basis: Union[List[Vector], Matrix], use_columns: bool = True) -> Vector:
        """
        Project a vector onto a subspace spanned by the given basis.
        Basis should be orthonormal for best results (use gram_schmidt first).
        
        Args:
            vector: The vector to project
            basis: Either a list of Vector objects or a Matrix whose columns/rows form the basis
            use_columns: If basis is a Matrix, True uses columns, False uses rows.
                        Ignored if basis is a List[Vector].
        
        Example:
            # With list of vectors
            v = Vector([1, 1, 1])
            basis = [Vector([1, 0, 0]), Vector([0, 1, 0])]
            proj = Ops.project_onto_subspace(v, basis)
            
            # With matrix (uses columns by default)
            v = Vector([1, 1, 1])
            A = Matrix([[1, 0], [0, 1], [0, 0]])  # xy-plane basis
            proj = Ops.project_onto_subspace(v, A)  # Project onto column space
            proj = Ops.project_onto_subspace(v, A, use_columns=False)  # Project onto row space
        """
        # Handle Matrix input
        if isinstance(basis, Matrix):
            if use_columns:
                basis = basis.column_vectors
            else:
                basis = basis.row_vectors
        
        if not basis:
            return Vector([Fraction(0)] * vector.dimension)
        
        # Check dimensions match
        dim = vector.dimension
        for b in basis:
            if b.dimension != dim:
                raise ValueError("All vectors must have the same dimension")
        
        # Project onto each basis vector and sum
        projection = Vector([Fraction(0)] * dim)
        for b in basis:
            # Project vector onto basis vector b
            coeff = vector.dot(b) / b.dot(b) if b.dot(b) != 0 else Fraction(0)
            projection = projection + coeff * b
        
        return projection
    
    @staticmethod
    def orthogonal_complement(vectors: Union[List[Vector], Matrix], dimension: Optional[int] = None, use_columns: bool = True) -> List[Vector]:
        """
        Find orthogonal complement of a subspace.
        Given vectors spanning a subspace, find basis for orthogonal complement.
        
        Args:
            vectors: Either a list of Vector objects or a Matrix
            dimension: The dimension of the ambient space. If None and vectors is a Matrix,
                      inferred from matrix dimensions. Required if vectors is a List[Vector].
            use_columns: If vectors is a Matrix, True uses columns, False uses rows.
                        Ignored if vectors is a List[Vector].
        
        Example:
            # With list of vectors
            v1 = Vector([1, 0, 0])
            v2 = Vector([0, 1, 0])
            # Orthogonal complement is z-axis
            complement = Ops.orthogonal_complement([v1, v2], 3)
            
            # With matrix (uses columns by default, dimension inferred)
            A = Matrix([[1, 0], [0, 1], [0, 0]])  # xy-plane
            complement = Ops.orthogonal_complement(A)  # z-axis
            complement = Ops.orthogonal_complement(A, use_columns=False)  # Use rows
        """
        # Handle Matrix input
        if isinstance(vectors, Matrix):
            if dimension is None:
                # Infer dimension from matrix
                if use_columns:
                    dimension = vectors.num_rows
                else:
                    dimension = vectors.num_cols
            
            if use_columns:
                vectors = vectors.column_vectors
            else:
                vectors = vectors.row_vectors
        
        if dimension is None:
            raise ValueError("dimension must be specified when vectors is a List[Vector]")
        
        if not vectors:
            # If no vectors, complement is entire space
            return [Vector([Fraction(1) if i == j else Fraction(0) 
                           for j in range(dimension)]) 
                   for i in range(dimension)]
        
        # Check dimensions
        for v in vectors:
            if v.dimension != dimension:
                raise ValueError("All vectors must have the specified dimension")
        
        # Create matrix with vectors as rows
        matrix = Matrix([v.components for v in vectors])
        
        # Null space of this matrix is the orthogonal complement
        return Ops.null_space(matrix)
