"""Encrypted file store for My Briefcase.
Folder: settings.BRIEF_DIR or /var/lib/xpertcreation/briefcase (outside the web root, owner only).
Key: settings.BRIEF_KEY, the environment, or BRIEF_KEY= in the API's .env (made by the installer; never printed)."""
import os
import re
import secrets

from cryptography.fernet import Fernet
from django.conf import settings

_F = None


def _dir():
    d = getattr(settings, "BRIEF_DIR", "") or "/var/lib/xpertcreation/briefcase"
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


def _key():
    k = getattr(settings, "BRIEF_KEY", "") or os.environ.get("BRIEF_KEY", "")
    if not k:
        try:
            env = open(os.path.join(str(settings.BASE_DIR), ".env")).read()
            m = re.search(r"^BRIEF_KEY=(.*)$", env, re.M)
            k = m.group(1).strip().strip('"\'') if m else ""
        except OSError:
            k = ""
    if not k:
        raise RuntimeError("Briefcase key missing")
    return k


def _f():
    global _F
    if _F is None:
        _F = Fernet(_key().encode())
    return _F


def _p(name):
    if not re.fullmatch(r"[a-f0-9]{32}\.bin", name or ""):
        raise ValueError("bad name")
    return os.path.join(_dir(), name)


def save(data):
    name = secrets.token_hex(16) + ".bin"
    tmp = _p(name) + ".part"
    with open(tmp, "wb") as fh:
        fh.write(_f().encrypt(data))
    os.chmod(tmp, 0o600)
    os.replace(tmp, _p(name))
    return name


def load(name):
    with open(_p(name), "rb") as fh:
        return _f().decrypt(fh.read())


def remove(name):
    try:
        os.remove(_p(name))
    except (OSError, ValueError):
        pass
