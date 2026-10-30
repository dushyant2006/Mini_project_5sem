"""
Unit tests for the CodeDrift Enterprise Web Platform & Server.
"""
import json
import threading
import time
from urllib.request import Request, urlopen
from codedrift.web.server import start_web_server


def test_web_server_endpoints():
    server = start_web_server(host="127.0.0.1", port=8999)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    base_url = "http://127.0.0.1:8999"

    try:
        # 1. Health check
        with urlopen(f"{base_url}/api/health") as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert data["status"] == "healthy"

        # 2. Scenarios list
        with urlopen(f"{base_url}/api/scenarios") as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert "scenarios" in data
            assert len(data["scenarios"]) > 0

        # 3. Static index.html
        with urlopen(f"{base_url}/index.html") as res:
            assert res.status == 200
            html = res.read().decode("utf-8")
            assert "CODEDRIFT" in html

        # 4. Analyze endpoint
        payload = json.dumps({
            "old_file": "data/fixtures/v1/payment_gateway.py",
            "new_file": "data/fixtures/v2/payment_gateway.py",
            "client_dir": "data/fixtures/client_app",
            "max_score": 0.0
        }).encode("utf-8")

        req = Request(f"{base_url}/api/analyze", data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req) as res:
            assert res.status == 200
            analysis = json.loads(res.read().decode("utf-8"))
            assert "diff" in analysis
            assert "blast_radius" in analysis
            assert "policy" in analysis
            assert "ml_prediction" in analysis
            assert "patches" in analysis

    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)
