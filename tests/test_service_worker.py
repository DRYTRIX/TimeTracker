def test_service_worker_serves_sw_js(client):
    resp = client.get("/service-worker.js")
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "application/javascript" in (resp.headers.get("Content-Type") or "")
    assert "const CACHE_NAME = 'timetracker-v1-ui1'" in text
    # Never intercept API or health probes (session + token auth; #746)
    assert "path.startsWith('/api/')" in text
    assert "path === '/_health'" in text


def test_manifest_legacy_redirect(client):
    resp = client.get("/manifest.webmanifest", follow_redirects=False)
    assert resp.status_code == 302
    assert "/static/manifest.json" in resp.headers.get("Location", "")


def test_offline_page_public(client):
    resp = client.get("/offline")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "timer is still running on the server" in body
    assert "Cache-Control" in resp.headers
