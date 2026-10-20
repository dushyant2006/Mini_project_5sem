"""
Lightweight REST API Service for CodeDrift (Standard Library HTTP).
Enables headless CI/CD webhooks and remote microservice integrations without external dependencies.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from ..parser.python_parser import PythonParser
from ..detection.diff_engine import DiffEngine
from ..impact.blast_radius import BlastRadiusAnalyzer
from ..guard.policy_engine import PolicyEngine
from ..core.config import GuardPolicy


class CodeDriftAPIHandler(BaseHTTPRequestHandler):
    """
    HTTP Request handler exposing CodeDrift functionality over JSON REST API.
    """

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path in ("/health", "/api/v1/health"):
            self._send_json(200, {
                "status": "healthy",
                "service": "CodeDrift Autonomous Guard API",
                "version": "1.0.0",
            })
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            req_data = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        if self.path == "/api/v1/diff":
            self._handle_diff(req_data)
        elif self.path == "/api/v1/guard":
            self._handle_guard(req_data)
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def _handle_diff(self, req: Dict[str, Any]) -> None:
        old_code = req.get("old_code", "")
        new_code = req.get("new_code", "")
        module_name = req.get("module_name", "target")

        parser = PythonParser()
        try:
            old_mod = parser.parse_code(old_code, module_name=module_name)
            new_mod = parser.parse_code(new_code, module_name=module_name)
            diff = DiffEngine().compare(old_mod, new_mod)
            self._send_json(200, diff.to_dict())
        except Exception as e:
            self._send_json(422, {"error": str(e)})

    def _handle_guard(self, req: Dict[str, Any]) -> None:
        old_file = req.get("old_file")
        new_file = req.get("new_file")
        client_dir = req.get("client_dir")
        max_score = float(req.get("max_score", 0.0))

        if not old_file or not new_file:
            self._send_json(400, {"error": "Missing old_file or new_file"})
            return

        parser = PythonParser()
        try:
            old_mod = parser.parse_file(old_file)
            new_mod = parser.parse_file(new_file)
            diff = DiffEngine().compare(old_mod, new_mod)

            report = None
            if client_dir:
                report = BlastRadiusAnalyzer().analyze(diff, client_dir=client_dir)

            policy = GuardPolicy(max_allowable_blast_radius=max_score)
            policy_res = PolicyEngine(policy).evaluate(diff, blast_report=report)

            self._send_json(200, {
                "decision": policy_res.decision.value,
                "exit_code": policy_res.exit_code,
                "summary": policy_res.summary,
                "violations": policy_res.violations,
                "blast_radius_score": policy_res.blast_radius_score,
                "breaking_count": len(diff.breaking_changes),
            })
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def log_message(self, format: str, *args) -> None:
        # Suppress noisy standard HTTP logs in test mode
        pass


def run_api_server(host: str = "0.0.0.0", port: int = 8000) -> HTTPServer:
    server_address = (host, port)
    httpd = HTTPServer(server_address, CodeDriftAPIHandler)
    return httpd
