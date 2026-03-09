# filesystem.py
from pathlib import Path

def find_repo_root(start: Path | None = None, *, max_levels: int = 6) -> Path | None:
    """
    Walk upward from 'start' (or this file's directory) until hitting a directory
    containing README.md (or .git). Returns the repo root Path or None.

    Works inside Streamlit multipage layouts regardless of CWD.
    """
    cur = (start or Path(__file__)).resolve()
    if cur.is_file():
        cur = cur.parent

    for _ in range(max_levels):
        if (cur / "README.md").exists():
            return cur
        if (cur / ".git").exists():
            return cur
        cur = cur.parent

    return None
