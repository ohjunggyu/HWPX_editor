import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_read_api():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    file_path = os.path.join(base_dir, "templates", "공문 예시.hwpx")

    if not os.path.exists(file_path):
        pytest.skip(f"Template not found: {file_path}")

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
        response = client.post("/api/v1/hwpx/read", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "blocks" in data
