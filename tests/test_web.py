import json

import pytest
from fastapi.testclient import TestClient

from englab.main import app
from englab.tools import CLIENT_TOOLS, TOOLS, execute

client = TestClient(app)


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t.slug)
def test_every_example_runs(tool):
    """Ogni esempio mostrato sul sito deve produrre un risultato serializzabile."""
    for ex in tool.examples:
        data = {f.name: f.default for f in tool.fields} | ex
        blocks = execute(tool.section, tool.slug, data)
        assert blocks and all("t" in b for b in blocks)
        json.dumps(blocks)


@pytest.mark.parametrize("url", ["/", "/privacy", "/come-si-scrive", "/analisi", "/fisica",
                                 *[t.url for t in TOOLS],
                                 *[f"/{t['section']}/{t['slug']}" for t in CLIENT_TOOLS]])
def test_pages_render(url):
    r = client.get(url)
    assert r.status_code == 200
    assert "<title>" in r.text


def test_tool_page_has_seo_metadata():
    r = client.get("/analisi/derivate")
    assert '<meta name="description"' in r.text
    assert 'rel="canonical"' in r.text
    assert "application/ld+json" in r.text


def test_unknown_pages_404():
    assert client.get("/nope").status_code == 404
    assert client.get("/analisi/nope").status_code == 404
    assert client.post("/api/analisi/nope", json={}).status_code == 404


def test_seo_files():
    assert "Sitemap:" in client.get("/robots.txt").text
    sm = client.get("/sitemap.xml").text
    assert all(t.url in sm for t in TOOLS)
    assert client.get("/ads.txt").status_code == 404  # AdSense non configurato


def test_api_success_and_errors():
    r = client.post("/api/analisi/derivate", json={"expr": "x^2", "var": "x", "ordine": "1"})
    assert r.status_code == 200
    assert r.json()["blocks"][0]["t"] == "result"
    r = client.post("/api/analisi/derivate", json={"expr": "__import__('os')"})
    assert r.status_code == 422
    assert "error" in r.json()
    r = client.post("/api/analisi/derivate", content="non json", headers={"content-type": "application/json"})
    assert r.status_code == 400


def test_rate_limit(monkeypatch):
    from englab import main
    monkeypatch.setattr(main.settings, "rate_per_minute", 2)
    main._hits.clear()
    codes = [client.post("/api/chimica/massa-molare", json={"formula": "H2O"},
                         headers={"x-forwarded-for": "10.0.0.9"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    main._hits.clear()
