"""Observed data: weather and solar activity. The only part of the program with network access.

Each source has its own module: a parser that takes text or bytes and returns a dict, with no network. update.py
downloads and saves. Sources, formats and privacy: docs/data-sources.md.
"""
