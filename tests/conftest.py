import pytest


@pytest.fixture
def sample_payload():
    return {"id": "evt_123", "amount": 999, "customer": "cus_456"}
