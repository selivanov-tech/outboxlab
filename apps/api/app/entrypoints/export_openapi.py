import json
import sys

from app.config import Settings, get_settings
from app.entrypoints.api import create_app


def production_openapi(settings: Settings) -> dict[str, object]:
    production = settings.model_copy(
        update={"app_env": "production", "internal_api_token": ""}
    )
    return create_app(production).openapi()


def render(schema: dict[str, object]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    sys.stdout.write(render(production_openapi(get_settings())))
