from sys import argv


if not len(argv) == 2:
    print("INCORRECT USAGE.")
    exit(1)

try:
    with open(f'{argv[1]}', 'r') as f:
        IN_FILE = f.read()
except:
    print("FILE DNE.")
    exit(1)


#VARS for reference/printing
vars = dict() #var name points to var type as is in the program - types will not change (as of now)


def parse_line_with_forgiveness_for_quotes_and_parenthesis(line: str) -> list:
    final = []
    curr = ""
    quote_mode: bool = False
    paren_mode: bool = False
    for char in line:
        if quote_mode:
            if char != '"':
                curr += char
            else:
                curr += '"'
                quote_mode = False
                continue
        elif paren_mode:
            if char != ')':
                curr += char
            else:
                curr += ')'
                paren_mode = False
                continue
        elif char == " " and curr:
            final.append(curr)
            curr = ""
        elif char == '"':
            curr += '"'
            quote_mode = True
        elif char == "(":
            curr += "("
            paren_mode = True
        else:
            curr += char

    if quote_mode:
        print("SYNTAX ERROR.")
        exit(1)
    if curr:
        final.append(curr)
    return final

#types
class _Num:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value
        self._type = None
    def interpret_num(self):
        self._type = "int"
class _Str:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value
        self.length = len(value)

class _For:
    def __init__(self, iterations=None):
        self.iterations = iterations

class _Print:
    def __init__(self, args=None):
        self.args = args

def parse_print(line: list) -> _Print:

    if len(line) > 1:
        return _Print(line[1::])
    else:
        return _Print()

def parse_var(line: list) -> _Num | _Str:
    global vars
    if (line[2][0] == "(" and line[2][-1] == ")") or line[2].isdigit():
        final = _Num(line[0], line[2])
        final.interpret_num()
        vars[final.name] = _Num
        return final
    elif line[2][0] == '"':
        final = _Str(line[0], line[2][1:-1])
        vars[final.name] = _Str
        return final
    else:
        print(line)
        print("SYNTAX ERROR.")
        exit(1)

def parse_for(line: list) -> _For:
    final = _For()
    if len(line) > 1:
        try:
            final.iterations = int(line[1])
        except:
            final.iterations = line[1]
    return final
def _Num_declaration(num: _Num) -> str:
    return f'{num._type} {num.name} = {num.value}'

def _Str_declaration(string: _Str) -> str:
    return f'char* {string.name} = "{string.value}"'


def _Print_string(printobject: _Print) -> str:
    def object_to_symbol(obj) -> str:
        if obj == _Str:
            return '%s'
        if obj == _Num:
            return '%d'
        else:
            print("OBJECT NOT SUPPORTED FOR PRINTING.")
            exit(1)
    var_queue = []

    if printobject.args:
        out = 'printf("'
        for argument in printobject.args:
            if (argument[0] == '"' and argument[-1] == '"'):
                out += f'{argument[1:-1]} '

            elif argument.isdigit():
                out += f'{argument} '
            elif argument in vars:
                out += f'{object_to_symbol(vars[argument])} '
                var_queue.append(argument)
            else:
                print("SYNTAX ERROR.")
                exit(1)

        out += '\\n"'
        if var_queue:
            for var in var_queue:
                out += f', {var}'
        out += ')'


        return out
    else:
        return 'printf("\\n")'
def _For_string(forobject: _For) -> str:
    if forobject.iterations == None:
        return "while (1) {"
    else:
        return f"for (int __i = 0; __i < {forobject.iterations}; __i++) {{"

def object_to_string(obj) -> str:
    if isinstance(obj, _For):
        return _For_string(obj)
    elif isinstance(obj, _Print):
        return _Print_string(obj)
    elif isinstance(obj, _Num):
        return _Num_declaration(obj)
    elif isinstance(obj, _Str):
        return _Str_declaration(obj)
    elif obj == "end":
        return "}"

_queue = []

#organize input string into array of arrays
L = IN_FILE.split('\n')
for x in range(len(L)):
    L[x] = L[x].strip()
    L[x] = parse_line_with_forgiveness_for_quotes_and_parenthesis(L[x])
OUT_TEXT = ""

#TODO: add variable libary additions
OUT_TEXT += "#include <stdio.h>\nint main() {"
for line in L:
    

    if len(line):
    
        match line[0]:
            case "print":
                _queue.append(parse_print(line))
            case "end":
                _queue.append("end")
            case "for":
                _queue.append(parse_for(line))
            case "#":
                continue
            case _:
                _queue.append(parse_var(line))

    else:
        continue
for s in _queue:
    if isinstance(s, _Str):
        OUT_TEXT += _Str_declaration(s)
        OUT_TEXT += ';'
    elif isinstance(s, _Num):
        OUT_TEXT += _Num_declaration(s)
        OUT_TEXT += ';'
    elif isinstance(s, _For):
        OUT_TEXT += _For_string(s)
    elif isinstance(s, _Print):
        OUT_TEXT += _Print_string(s)
        OUT_TEXT += ';'
    elif s == 'end':
        OUT_TEXT += '}'
OUT_TEXT += "return 0;}"



with open("__out.c", "w") as OUT_FILE:
    OUT_FILE.write(OUT_TEXT)
