import os
import pytest

os.environ.setdefault("KITCHENOWL_URL", "https://kitchenowl.test")
os.environ.setdefault("KITCHENOWL_TOKEN", "test-token")
os.environ.setdefault("KITCHENOWL_HOUSEHOLD_ID", "1")

from kitchenowl import KitchenOwlClient, KitchenOwlError

@pytest.fixture
def client():
    return KitchenOwlClient()

@pytest.fixture
def mock_get(client, monkeypatch):
    def factory(return_value, status_code=200):
        from unittest.mock import Mock
        mock_resp = Mock()
        mock_resp.status_code = status_code
        mock_resp.content = b"x"
        mock_resp.json.return_value = return_value
        monkeypatch.setattr(client.session, "request", lambda *a, **kw: mock_resp)
        return mock_resp
    return factory
