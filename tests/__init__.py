"""Tests with no hardware and no network. Run them from the repository root: python3 -m unittest discover -s tests -t .

This file runs first, so the program's folders point to a temporary place before anything is imported.
"""
import os
import tempfile

FOLDER = tempfile.mkdtemp(prefix="luces-tests-")
for variable, name in (("LUCES_CONTROL", "control"), ("LUCES_DATA", "data"), ("LUCES_RUN", "run")):
    os.environ[variable] = os.path.join(FOLDER, name)
    os.makedirs(os.environ[variable])
