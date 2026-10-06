"""Applicazione web EngLab (FastAPI + template Jinja)."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .core import sandbox
from .core.parsing import ParseError
from .tools import CLIENT_BY_KEY, CLIENT_TOOLS, SECTIONS, TOOLS, TOOLS_BY_KEY, execute

BASE = Path(__file__).parent


class Settings:
    """Configurazione da variabili d'ambiente (vedi .env.example)."""

    site_url = os.environ.get("ENGLAB_SITE_URL", "http://localhost:8000").rstrip("/")
    site_name = os.environ.get("ENGLAB_SITE_NAME", "EngLab")
    adsense_client = os.environ.get("ENGLAB_ADSENSE_CLIENT", "")  # es. ca-pub-1234567890
    adsense_slot = os.environ.get("ENGLAB_ADSENSE_SLOT", "")
    donate_url = os.environ.get("ENGLAB_DONATE_URL", "")  # es. https://ko-fi.com/tuonome
    analytics_domain = os.environ.get("ENGLAB_PLAUSIBLE_DOMAIN", "")  # analytics senza cookie
    contact_email = os.environ.get("ENGLAB_CONTACT_EMAIL", "")
    max_concurrent = int(os.environ.get("ENGLAB_MAX_CONCURRENT", "4"))
    rate_per_minute = int(os.environ.get("ENGLAB_RATE_PER_MINUTE", "30"))


settings = Settings()
app = FastAPI(title="EngLab", version=__version__, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
templates.env.globals.update(settings=settings, sections=SECTIONS, tools=TOOLS,
                             client_tools=CLIENT_TOOLS, version=__version__, year=date.today().year)

_slots = threading.BoundedSemaphore(settings.max_concurrent)
_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= settings.rate_per_minute:
            return True
        q.append(now)
        if len(_hits) > 50_000:  # evita crescita illimitata della memoria
            _hits.clear()
        return False


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return response


# --------------------------------------------------------------------------- API

@app.post("/api/{section}/{slug}")
async def api(request: Request, section: str, slug: str):
    if (section, slug) not in TOOLS_BY_KEY:
        raise HTTPException(404)
    if _rate_limited(_client_ip(request)):
        return JSONResponse({"error": "Troppe richieste: aspetta un minuto e riprova."}, status_code=429)
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Richiesta non valida."}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"error": "Richiesta non valida."}, status_code=400)
    data = {k: v for k, v in data.items() if isinstance(v, (str, int, float))}

    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(_compute, section, slug, data)


def _compute(section: str, slug: str, data: dict) -> JSONResponse:
    if not _slots.acquire(timeout=15):
        return JSONResponse({"error": "Il server è molto carico, riprova tra poco."}, status_code=503)
    try:
        blocks = sandbox.run(execute, section, slug, data)
        return JSONResponse({"blocks": blocks})
    except ParseError as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)
    except sandbox.ComputationTimeout as exc:
        return JSONResponse({"error": str(exc)}, status_code=408)
    except Exception:
        return JSONResponse({"error": "Non sono riuscito a completare il calcolo. "
                                      "Controlla l'input o prova una forma equivalente."}, status_code=500)
    finally:
        _slots.release()


# --------------------------------------------------------------------------- SEO

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {settings.site_url}/sitemap.xml\n"


@app.get("/sitemap.xml")
def sitemap():
    urls = ["/", "/come-si-scrive", *[f"/{s}" for s in SECTIONS], *[t.url for t in TOOLS],
            *[f"/{t['section']}/{t['slug']}" for t in CLIENT_TOOLS]]
    today = date.today().isoformat()
    body = "".join(f"<url><loc>{settings.site_url}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return Response(xml, media_type="application/xml")


@app.get("/ads.txt", response_class=PlainTextResponse)
def ads_txt():
    if not settings.adsense_client:
        raise HTTPException(404)
    pub = settings.adsense_client.replace("ca-", "")
    return f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n"


@app.get("/healthz", response_class=PlainTextResponse)
def health():
    return "ok"


# --------------------------------------------------------------------------- pagine

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})


@app.get("/come-si-scrive", response_class=HTMLResponse)
def syntax(request: Request):
    return templates.TemplateResponse(request, "sintassi.html", {})


@app.get("/{section}", response_class=HTMLResponse)
def section_page(request: Request, section: str):
    if section not in SECTIONS:
        raise HTTPException(404)
    items = [t for t in TOOLS if t.section == section]
    client = [t for t in CLIENT_TOOLS if t["section"] == section]
    return templates.TemplateResponse(request, "section.html",
                                      {"section": section, "items": items, "client": client})


@app.get("/{section}/{slug}", response_class=HTMLResponse)
def tool_page(request: Request, section: str, slug: str):
    tool = TOOLS_BY_KEY.get((section, slug))
    if tool:
        related = [t for t in TOOLS if t.section == section and t.slug != slug]
        return templates.TemplateResponse(request, "tool.html", {"tool": tool, "related": related})
    client = CLIENT_BY_KEY.get((section, slug))
    if client:
        return templates.TemplateResponse(request, client["template"], {"tool": client})
    raise HTTPException(404)
