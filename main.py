"""
IW-08 GoogleImages — Google Images Results
Iron Warrior #8 — Visuel, thumbnails + metadata.
Attaque : SerpWow ($120/10K)
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re, json
import sys
sys.path.insert(0, '/home/user/iron_warriors/shared')
from base import create_app, fetch_html, clean_text, get_timestamp, measure_latency
import time

app = create_app("IW-08 GoogleImages", "Google Images results — thumbnails + metadata")

class ImageResult(BaseModel):
    title: str
    image_url: str
    source_url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    position: int

class ImageResponse(BaseModel):
    query: str
    engine: str
    results: List[ImageResult]
    timestamp: str
    latency_ms: int

@app.get("/search", response_model=ImageResponse)
async def google_images(
    q: str = Query(..., description="Image search query"),
    num: int = Query(20, ge=1, le=100),
    gl: str = Query("us"),
    hl: str = Query("en"),
):
    start = time.time()
    url = f"https://www.google.com/search?q={quote_plus(q)}&tbm=isch&num={num}&gl={gl}&hl={hl}"
    try:
        html = await fetch_html(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Images fetch failed: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()

    # Google Images embeds data in script tags — extract image URLs
    for script in soup.find_all('script'):
        text = script.string or ""
        # Look for image data patterns
        matches = re.findall(r'"ou":"(https?://[^"]+)".*?"tu":"(https?://[^"]+)".*?"pt":"([^"]*)".*?"ru":"(https?://[^"]+)"', text)
        for ou, tu, pt, ru in matches:
            if ou in seen:
                continue
            seen.add(ou)
            results.append(ImageResult(
                title=pt.replace('\\u0026', '&'),
                image_url=ou.replace('\\u0026', '&'),
                source_url=ru.replace('\\u0026', '&'),
                thumbnail_url=tu.replace('\\u0026', '&'),
                position=len(results) + 1,
            ))
            if len(results) >= num:
                break

    # Fallback: parse img tags
    if not results:
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ""
            if src.startswith('http') and 'gstatic' not in src and src not in seen:
                seen.add(src)
                alt = img.get('alt', '')
                results.append(ImageResult(
                    title=alt, image_url=src, source_url="",
                    position=len(results) + 1,
                ))
                if len(results) >= num:
                    break

    return ImageResponse(
        query=q, engine="google_images", results=results,
        timestamp=get_timestamp(), latency_ms=measure_latency(start),
    )
