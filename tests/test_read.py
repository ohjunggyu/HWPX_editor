import asyncio
import httpx
import os
import sys


async def test_read_api():
    file_path = "modified_test.hwpx"
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path}")
        sys.exit(1)

    url = "http://127.0.0.1:8000/api/v1/hwpx/read"
    print(f"Testing the API at {url} with file {file_path}...")

    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            response = await client.post(url, files=files, timeout=10.0)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("Response Data:")
            print(f"File Name: {data.get('file_name')}")
            blocks = data.get("blocks", [])
            print(f"Found {len(blocks)} blocks.")
            for i, block in enumerate(blocks[:10]):  # Print first 10
                print(f"  [{block['block_id']}] ({block['type']}) : {block['text']}")
            if len(blocks) > 10:
                print("  ... and more.")
        else:
            print(f"Error Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_read_api())
