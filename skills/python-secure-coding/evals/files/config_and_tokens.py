# Intentionally unsafe patterns fixture. Do not deploy.
import pickle
import random
from pathlib import Path

API_SECRET = "hardcoded-prod-secret-do-not-use"


def load_config(path: str):
    data = Path(path).read_bytes()
    return pickle.loads(data)


def session_token() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(32))
