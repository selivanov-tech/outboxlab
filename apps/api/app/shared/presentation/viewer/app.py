from pathlib import Path

from starlette.staticfiles import StaticFiles

VIEWER_STATIC_DIR = Path(__file__).parent / "static"


def viewer_app() -> StaticFiles:
    return StaticFiles(directory=VIEWER_STATIC_DIR, html=True)
