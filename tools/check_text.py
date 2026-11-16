#!/usr/bin/env python3
"""Finds text meant to be hidden from people. A filter, not a guarantee: see docs/threat-model.md.

    python3 tools/check_text.py                  every text file of the repository
    python3 tools/check_text.py --stdin < x.md   text from an issue or comment, before an agent reads it

Exit code 1 means something was found.
"""
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_FOLDERS = {".git", "__pycache__", ".venv", "build", "dist"}
TEXT_FILES = (".py", ".md", ".toml", ".yml", ".yaml", ".sh", ".service", ".timer", ".desktop", ".txt")
NAMED = {0x00AD: "soft hyphen", 0x180E: "mongolian vowel separator", 0x2060: "word joiner", 0xFEFF: "byte order mark"}
HIDDEN_MARKUP = (
    (re.compile(r"<!--.*?-->", re.S), "HTML comment"),
    (re.compile(r"<(?:details|summary|style|script|iframe|object|embed)\b", re.I), "HTML tag that can hide text"),
    (re.compile(r"!\[[^\]]{40,}\]\("), "long image alt text"),
    (re.compile(r"&#x?[0-9a-f]+;", re.I), "HTML entity"),
)


def hidden_characters(text):
    """(line, description) for each character a person cannot see."""
    found = []
    for line, content in enumerate(text.splitlines(), 1):
        for character in content:
            code = ord(character)
            if code in NAMED:
                found.append((line, NAMED[code]))
            elif 0x200B <= code <= 0x200F or 0x202A <= code <= 0x202E or 0x2066 <= code <= 0x2069:
                found.append((line, f"invisible or bidirectional character U+{code:04X}"))
            elif 0xE0000 <= code <= 0xE007F:
                found.append((line, f"tag character U+{code:04X}"))
            elif unicodedata.category(character) == "Cc" and character not in "\t":
                found.append((line, f"control character U+{code:04X}"))
    return found


def hidden_markup(text):
    """(line, description) for markup that renders as nothing, or as less than what it holds."""
    return [(text.count("\n", 0, m.start()) + 1, description) for pattern, description in HIDDEN_MARKUP for m in pattern.finditer(text)]


def check_public_text(text):
    return sorted(hidden_characters(text) + hidden_markup(text))


def repository_files(root=ROOT):
    for folder, subfolders, names in os.walk(root):
        subfolders[:] = [s for s in subfolders if s not in SKIP_FOLDERS]
        for name in names:
            if name.endswith(TEXT_FILES):
                yield os.path.join(folder, name)


def check_repository(root=ROOT):
    found = []
    for path in repository_files(root):
        with open(path, encoding="utf-8") as f:
            found += [(os.path.relpath(path, root), line, what) for line, what in hidden_characters(f.read())]
    return found


def main(argv):
    if argv[:1] == ["--stdin"]:
        found = check_public_text(sys.stdin.read())
        for line, what in found:
            print(f"line {line}: {what}")
    else:
        found = check_repository()
        for path, line, what in found:
            print(f"{path}:{line}: {what}")
    if found:
        print(f"{len(found)} found. Read the raw text before going on.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
