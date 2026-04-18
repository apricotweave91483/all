#!/usr/bin/env python3

from sys import argv
s = argv[1]
s1 = set(s[0:3])
s2 = set(s[3:6])
s3 = set(s[6:9])
s4 = set(s[9:12])
def good(string: str):
    for c in string:
        if not c in s1 and not c in s2 and not c in s3 and not c in s4:
            return 0
    return 1

with open("cleaned_words.txt", "r") as f:
    words = [string.strip() for string in f.readlines() if good(string.strip())]

viable = []

def acceptable_solution(words: list[str]):
    total = set()
    for word in words:
        for c in set(word):
            total.add(c)
    for c in s1:
        if not c in total:
            return 0
    for c in s2:
        if not c in total:
            return 0
    for c in s3:
        if not c in total:
            return 0
    for c in s4:
        if not c in total:
            return 0
    return 1

def mtch(char: str) -> str:
    if char in s1:
        return "a"
    elif char in s2:
        return "b"
    elif char in s3:
        return "c"
    elif char in s4:
        return "d"

def string_good(string: str):
    last = mtch(string[0])
    for char in string[1:]:
        now = mtch(char)
        if now == last:
            return 0
        last = now
    return 1

for string in words:
    if string_good(string):
        viable.append(string)

print(f"viable words: {len(viable)}")

print("2 WORD SOLUTIONS:")

for string1 in viable:
    for string2 in viable:
        sol = (string1, string2)
        if acceptable_solution(sol) and string1[-1] == string2[0]:
            print(sol)
input("PRINT 3 WORD SOLUTIONS?")
print("3 WORD SOLUTIONS:")

for string1 in viable:
    for string2 in viable:
        for string3 in viable:
            sol = (string1, string2, string3)
            if acceptable_solution(sol) and string1[-1] == string2[0] and string2[-1] == string3[0]:
                print(sol)
