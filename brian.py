"""
Upload a PBN file to BrianBridge. Copied from upload.py in the PBNCreator project.

The slot and password are read from brian.json next to this file. That file is
not in git (see brian.json.example for its format).
"""

import json
from pathlib import Path

URL = "https://www.brianbridge.net/cgi-bin/brian2puthandrecordxml.cgi"
CONFIG = Path(__file__).parent / "brian.json"
TIMEOUT = 30  # seconds


def load_config():
    """Return {"slot": ..., "password": ...} from brian.json"""
    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        return {"slot": config["slot"], "password": config["password"]}
    except FileNotFoundError:
        raise RuntimeError(f"{CONFIG.name} not found. Copy brian.json.example and fill it in")
    except (ValueError, KeyError):
        raise RuntimeError(f"{CONFIG.name} must contain a slot and a password")


def upload_pbn(filename):
    """Upload a pbn file and return the requests response. Raises on a network error."""
    import requests  # not needed until the first upload

    path = Path(filename)
    config = load_config()
    with open(path, "rb") as f:
        params = {"SLOT": config["slot"], "PASSWORD": config["password"]}
        data = {"name": "upload", "filename": path.name}
        files = {"file": f}
        return requests.post(URL, files=files, data=data, params=params, timeout=TIMEOUT)
