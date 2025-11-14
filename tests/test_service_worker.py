import re


def test_service_worker_serves_assets(client):
    resp = client.get('/service-worker.js')
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    # Ensure JS content type and presence of cache list with known asset
    assert 'application/javascript' in (resp.headers.get('Content-Type') or '')
    assert 'dist/output.css' in text
    assert 'enhanced-ui.js' in text
    # Basic sanity: ASSETS array present
    assert 'const ASSETS=' in text

