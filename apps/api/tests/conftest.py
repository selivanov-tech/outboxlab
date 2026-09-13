from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def contracts_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "contracts"
        if (candidate / "events").is_dir():
            return candidate
    raise RuntimeError("contracts/ directory not found above the api tests")
