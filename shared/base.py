"""
PERTURABO — Iron Warriors Shared Base
Module commun à tous les Iron Warriors.
Chaque wrapper FastAPI hérite de cette base.
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import asyncio
import time
import re
from urllib.parse import quote_plus, urlencode
from bs4 import BeautifulSoup

# === Configuration globale ===
DEFAULT_TIMEOUT = 30
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

# === Modèles de réponse ===

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    position: int
    display_url: Optional[str] = None

class SERPResponse(BaseModel):
    query: str
    engine: str
    total_results: Optional[str] = None
    results: List[SearchResult]
    related_searches: List[str] = []
    people_also_ask: List[str] = []
    timestamp: str
    latency_ms: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

# === Client HTTP réutilisable ===

async def fetch_html(url: str, headers: Optional[Dict] = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch HTML content with rotating user agent."""
    h = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, headers=h)
        resp.raise_for_status()
        return resp.text

async def fetch_html_mobile(url: str, headers: Optional[Dict] = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch HTML with mobile user agent."""
    h = {"User-Agent": MOBILE_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, headers=h)
        resp.raise_for_status()
        return resp.text

# === Helpers de parsing ===

def clean_text(text: str) -> str:
    """Nettoie le texte : espaces, retours, caractères parasites."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def html_to_markdown(html: str) -> str:
    """Convertit un bloc HTML en Markdown simplifié."""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(['script', 'style', 'noscript']):
        tag.decompose()
    # Liens
    for a in soup.find_all('a', href=True):
        a.replace_with(f"[{a.get_text()}]({a['href']})")
    # Titres
    for level in range(1, 7):
        for h in soup.find_all(f'h{level}'):
            h.replace_with(f"\n{'#' * level} {h.get_text()}\n")
    # Listes
    for li in soup.find_all('li'):
        li.replace_with(f"- {li.get_text()}\n")
    # Paragraphes
    for p in soup.find_all('p'):
        p.replace_with(f"\n{p.get_text()}\n")
    return clean_text(soup.get_text())

def get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().astimezone().isoformat()

def measure_latency(start: float) -> int:
    return int((time.time() - start) * 1000)

# === Factory FastAPI ===

def create_app(iw_name: str, iw_specialization: str) -> FastAPI:
    """Crée une app FastAPI standardisée pour un Iron Warrior."""
    app = FastAPI(
        title=f"Iron Warrior — {iw_name}",
        description=f"{iw_specialization}\n\nPart of PERTURABO Iron Warriors fleet.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/")
    async def root():
        return {
            "iron_warrior": iw_name,
            "specialization": iw_specialization,
            "status": "operational",
            "endpoints": [r.path for r in app.routes if hasattr(r, 'path') and r.path != "/"],
        }

    @app.get("/health")
    async def health():
        return {"status": "healthy", "iron_warrior": iw_name}

    return app
