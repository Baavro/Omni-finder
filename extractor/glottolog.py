# extractor/glottolog.py
import httpx, asyncio
from .orchestrator import fetch

BASE = "https://glottolog.org/resource/languoid/id/{code}.json"

async def get_glotto(code: str) -> dict:
    url = BASE.format(code=code)
    async with httpx.AsyncClient() as client:
        try:
            return await fetch(client, url, key=f"gl_{code}")
        except Exception:
            return {}

async def for_glottocodes(codes: list[str]) -> dict:
    out = {}
    for gc in codes:
        out[gc] = await get_glotto(gc)
        await asyncio.sleep(0.05)
    return out
