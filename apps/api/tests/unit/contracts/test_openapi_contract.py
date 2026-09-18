from pathlib import Path

from app.config import get_settings
from app.entrypoints.export_openapi import production_openapi, render


def test_committed_openapi_contract_matches_the_production_app(
    contracts_dir: Path,
) -> None:
    committed = (contracts_dir / "openapi/api-v1.json").read_text()

    assert committed == render(production_openapi(get_settings())), (
        "contracts/openapi/api-v1.json is stale: run `make openapi` "
        "and `pnpm api:generate` in apps/web"
    )
