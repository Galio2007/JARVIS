import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load():
    with open(ROOT / "config.toml", "rb") as f:
        c = tomllib.load(f)
    c["paths"] = {k: Path(v).expanduser() for k, v in c["paths"].items()}
    return c
