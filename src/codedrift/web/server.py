"""
Enterprise Web Server and API Gateway for CodeDrift.
Serves the web platform and handles real-time contract analysis requests over HTTP.
"""
import json
import mimetypes
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional

from ..parser.python_parser import PythonParser
from ..detection.diff_engine import DiffEngine
from ..detection.semver_checker import SemVerAuditor
from ..impact.blast_radius import BlastRadiusAnalyzer
from ..guard.policy_engine import PolicyEngine
from ..remediation.patch_generator import PatchGenerator
from ..remediation.migration_guide import MigrationGuideSynthesizer
from ..remediation.advisor import RemediationAdvisor
from ..ml.predictor import DegradationPredictor
from ..core.config import GuardPolicy
from ..core.database import AuditDatabase


WEB_ROOT = Path(__file__).parent


class CodeDriftWebHandler(SimpleHTTPRequestHandler):
    """
    HTTP handler serving both static enterprise dashboard assets
    and JSON REST analysis endpoints.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(WEB_ROOT / "index.html", "text/html")
        elif self.path == "/api/health":
            self._send_json(200, {
                "status": "healthy",
                "service": "CodeDrift Enterprise Web Platform",
                "version": "1.0.0",
            })
        elif self.path == "/api/scenarios":
            self._handle_scenarios()
        elif self.path == "/api/history":
            db = AuditDatabase()
            history = db.get_recent_runs(limit=15)
            stats = db.get_database_stats()
            self._send_json(200, {"history": history, "stats": stats})
        else:
            # Static file fallback
            file_path = WEB_ROOT / self.path.lstrip("/")
            if file_path.is_file():
                mime, _ = mimetypes.guess_type(str(file_path))
                self._serve_file(file_path, mime or "application/octet-stream")
            else:
                self._send_json(404, {"error": f"Resource not found: {self.path}"})

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            req_data = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_json(400, {"error": f"Malformed JSON request: {e}"})
            return

        if self.path == "/api/analyze":
            self._handle_analyze(req_data)
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def _serve_file(self, path: Path, content_type: str) -> None:
        try:
            content = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json(500, {"error": f"Failed to read file: {e}"})

    def _handle_scenarios(self) -> None:
        scenarios = [
            {
                "id": "payment_gateway_v2",
                "name": "Scenario 1: Payment Gateway (Parameter Removed: 'currency')",
                "description": "The library removed the 'currency' parameter from process_payment(). Our checkout code crashes because it still passes currency='USD'.",
                "old_file": "data/fixtures/v1/payment_gateway.py",
                "new_file": "data/fixtures/v2/payment_gateway.py",
                "client_dir": "data/fixtures/client_app",
            },
            {
                "id": "auth_service_v2",
                "name": "Scenario 2: User Login (Required Parameter Added: 'mfa_code')",
                "description": "The authentication library now requires a mandatory 'mfa_code' parameter. Our login page crashes because it does not pass MFA yet.",
                "old_file": "data/fixtures/v1/auth_service.py",
                "new_file": "data/fixtures/v2/auth_service.py",
                "client_dir": "data/fixtures/client_app",
            },
            {
                "id": "notification_service_v2",
                "name": "Scenario 3: Email Alerts (Whole Function Deleted: 'send_email')",
                "description": "The email library deleted the entire send_email() function. Our alert service immediately fails with an AttributeError at runtime.",
                "old_file": "data/fixtures/v1/notification_service.py",
                "new_file": "data/fixtures/v2/notification_service.py",
                "client_dir": "data/fixtures/client_app",
            },
            {
                "id": "storage_lib_v1_1",
                "name": "Scenario 4: Cloud Storage (Safe: Backward-Compatible Update)",
                "description": "The library added an optional 'encryption' parameter with a safe default. Our code runs normally without any errors. Quality gate passes!",
                "old_file": "data/fixtures/v1/storage_lib.py",
                "new_file": "data/fixtures/v2/storage_lib.py",
                "client_dir": "data/fixtures/client_app",
            }
        ]
        self._send_json(200, {"scenarios": scenarios})

    def _handle_analyze(self, req: Dict[str, Any]) -> None:
        project_root = WEB_ROOT.parent.parent.parent
        old_file = req.get("old_file", "data/fixtures/v1/payment_gateway.py")
        new_file = req.get("new_file", "data/fixtures/v2/payment_gateway.py")
        client_dir = req.get("client_dir", "data/fixtures/client_app")
        max_score = float(req.get("max_score", 0.0))

        # Resolve relative paths against workspace root
        old_path = project_root / old_file if not Path(old_file).is_absolute() else Path(old_file)
        new_path = project_root / new_file if not Path(new_file).is_absolute() else Path(new_file)
        client_path = project_root / client_dir if not Path(client_dir).is_absolute() else Path(client_dir)

        parser = PythonParser()
        try:
            old_mod = parser.parse_file(old_path)
            new_mod = parser.parse_file(new_path)
        except Exception as e:
            self._send_json(422, {"error": f"AST Parser error: {e}"})
            return

        diff = DiffEngine().compare(old_mod, new_mod)

        report = None
        if client_path.is_dir():
            report = BlastRadiusAnalyzer().analyze(diff, client_dir=client_path)

        policy = GuardPolicy(max_allowable_blast_radius=max_score)
        gate_res = PolicyEngine(policy).evaluate(diff, blast_report=report)

        auditor = SemVerAuditor()
        semver_res = auditor.audit_bump("1.0.0", "2.0.0", diff)

        predictor = DegradationPredictor()
        ml_pred = predictor.predict(diff, blast_report=report)

        patcher = PatchGenerator()
        patches = patcher.generate_patches(report) if report else []

        guide_synth = MigrationGuideSynthesizer()
        guide = guide_synth.generate_markdown(report) if report else ""

        advisor = RemediationAdvisor(patcher)
        remediation_actions = advisor.generate_plan(report, patches)

        # Persist audit record in SQLite database
        scenario_name = req.get("scenario_name", Path(old_file).stem)
        db = AuditDatabase()
        run_id = db.record_run(
            scenario_name=scenario_name,
            old_file=str(old_file),
            new_file=str(new_file),
            client_dir=str(client_dir),
            decision=gate_res.decision.value if hasattr(gate_res.decision, "value") else str(gate_res.decision),
            blast_radius_score=report.blast_radius_score if report else 0.0,
            diff_data=diff.to_dict(),
            blast_data=report.to_dict() if report else None,
            ml_data=ml_pred.to_dict(),
            remediation_items=remediation_actions,
        )

        db_stats = db.get_database_stats()

        self._send_json(200, {
            "run_id": run_id,
            "diff": diff.to_dict(),
            "blast_radius": report.to_dict() if report else None,
            "policy": gate_res.to_dict(),
            "semver": semver_res,
            "ml_prediction": ml_pred.to_dict(),
            "patches": [p.to_dict() for p in patches],
            "migration_guide": guide,
            "remediation_actions": remediation_actions,
            "database_stats": db_stats,
        })

    def log_message(self, format: str, *args) -> None:
        pass


def start_web_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    server = HTTPServer((host, port), CodeDriftWebHandler)
    return server
