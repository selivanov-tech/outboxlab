import uuid


def make_message_id(domain: str) -> str:
    return f"<{uuid.uuid4().hex}@{domain}>"
