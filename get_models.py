import httpx
import asyncio

async def main():
    try:
        res = await httpx.AsyncClient().get('http://localhost:11435/api/tags')
        models = [m['name'] for m in res.json().get('models', [])]
        print("Available models:")
        for m in models:
            print(" -", m)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
