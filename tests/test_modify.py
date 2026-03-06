import json
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_modify_api():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    file_path = os.path.join(base_dir, "templates", "공문 예시.hwpx")

    if not os.path.exists(file_path):
        pytest.skip(f"Template not found: {file_path}")

    modifications = [
        {"block_id": "sec0_tbl0_r0_c0", "target_text": "로고", "replace_text": "테스트텍스트변환"}
    ]
    modifications_json = json.dumps(modifications)

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
        data = {"modifications": modifications_json}
        response = client.post("/api/v1/hwpx/modify", files=files, data=data)

    assert response.status_code == 200
    assert len(response.content) > 0
