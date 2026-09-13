import json
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator

from app.contexts.campaign.domain.send_job import SendJobPayload


def test_send_job_payload_matches_contract(contracts_dir: Path) -> None:
    schema = json.loads((contracts_dir / "jobs/send_job/v1.json").read_text())
    payload = SendJobPayload(
        campaign_id=uuid.uuid7(),
        lead_id=uuid.uuid7(),
        step_id=uuid.uuid7(),
        step_position=1,
        to_email="lead@example.com",
        subject="Hello",
        body="First touch",
    ).model_dump(mode="json")

    Draft202012Validator(
        schema, format_checker=Draft202012Validator.FORMAT_CHECKER
    ).validate(payload)
    assert set(payload) == set(schema["required"])
