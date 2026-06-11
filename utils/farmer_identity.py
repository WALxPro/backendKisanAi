from __future__ import annotations

from uuid import uuid4


def generate_farmer_id() -> str:
    return f"FRM-{uuid4().hex[:12].upper()}"
