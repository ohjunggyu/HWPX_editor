import asyncio
import httpx
import os
import sys
import json


async def test_modify_api():
    file_path = "example files/공문 예시.hwpx"
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        sys.exit(1)

    url = "http://127.0.0.1:8000/api/v1/hwpx/modify"
    print(f"Testing the API at {url} with file {file_path}...")

    # Based on the read output, sec0_tbl0_r0_c1 has text "주식회사 abc 제안서"
    # Wait, the output for sec0_tbl0_r0_c1 was: "주식회사 abc 제안    로 하는 바입니다.아래 내용과 같이 협조해주실 것을 요청" (probably mixed from the whole document due to my earlier script printing things strangely, or maybe it really is that).
    # Let's change "로고" in sec0_tbl0_r0_c0 to "새로운회사로고"

    modifications = [
        {"block_id": "sec0_tbl0_r0_c0", "target_text": "로고", "replace_text": "테스트텍스트변환"}
    ]

    modifications_json = json.dumps(modifications)

    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = {"modifications": modifications_json}
            response = await client.post(url, files=files, data=data, timeout=10.0)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            base_name = os.path.basename(file_path)
            output_filepath = f"modified_{base_name}"
            with open(output_filepath, "wb") as out_f:
                out_f.write(response.content)
            print(f"Successfully saved modified file to {output_filepath}")
        else:
            print(f"Error Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_modify_api())
