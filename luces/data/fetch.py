"""The only door to the internet. HTTPS only, with small limits, so a bad server cannot do much."""
import subprocess

USER_AGENT = "luces/0.1"


class InvalidData(ValueError):
    pass


FETCH_ERRORS = (InvalidData, OSError, subprocess.SubprocessError)


def fetch_bytes(url):
    r = subprocess.run(["/usr/bin/curl", "-fsS", "--proto", "=https", "--max-time", "20", "--max-filesize", "65536",
                        "-A", USER_AGENT, url], capture_output=True, timeout=30)
    if r.returncode != 0:
        raise InvalidData(f"curl {r.returncode}: {r.stderr.decode(errors='replace').strip()[:120]}")
    return r.stdout


def fetch_text(url):
    return fetch_bytes(url).decode("utf-8", "replace")
