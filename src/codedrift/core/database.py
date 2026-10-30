"""
Embedded SQLite Database Repository for CodeDrift.
Persists audit runs, API contract change logs, and remediation tasks.
Zero external configuration, built on Python standard library sqlite3.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "codedrift_audit.db"


class AuditDatabase:
    """
    Manages historical persistence of dependency check runs,
    breaking changes detected, and suggested remediation steps.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Audit Runs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                old_file TEXT NOT NULL,
                new_file TEXT NOT NULL,
                client_dir TEXT NOT NULL,
                decision TEXT NOT NULL,
                blast_radius_score REAL NOT NULL,
                total_changes INTEGER NOT NULL,
                breaking_changes INTEGER NOT NULL,
                reachable_sites INTEGER NOT NULL,
                risk_tier TEXT NOT NULL
            );
            """)

            # 2. Remediation Tasks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS remediation_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                file_path TEXT NOT NULL,
                target_symbol TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                human_action TEXT NOT NULL,
                code_before TEXT,
                code_after TEXT,
                patch_diff TEXT,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (run_id) REFERENCES audit_runs (id) ON DELETE CASCADE
            );
            """)
            conn.commit()

    def record_run(
        self,
        scenario_name: str,
        old_file: str,
        new_file: str,
        client_dir: str,
        decision: str,
        blast_radius_score: float,
        diff_data: Dict[str, Any],
        blast_data: Optional[Dict[str, Any]],
        ml_data: Optional[Dict[str, Any]],
        remediation_items: List[Dict[str, Any]],
    ) -> int:
        """
        Inserts a completed audit run and its corresponding remediation tasks.
        Returns the new run ID.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_chg = diff_data.get("total_changes", 0)
        break_chg = diff_data.get("breaking_count", 0)
        reach_cnt = blast_data.get("total_reachable_call_sites", 0) if blast_data else 0
        risk_tier = ml_data.get("risk_tier", "UNKNOWN") if ml_data else "UNKNOWN"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_runs (
                timestamp, scenario_name, old_file, new_file, client_dir,
                decision, blast_radius_score, total_changes, breaking_changes,
                reachable_sites, risk_tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, scenario_name, old_file, new_file, client_dir,
                decision, blast_radius_score, total_chg, break_chg,
                reach_cnt, risk_tier
            ))
            run_id = cursor.lastrowid

            for item in remediation_items:
                cursor.execute("""
                INSERT INTO remediation_tasks (
                    run_id, file_path, target_symbol, issue_type,
                    human_action, code_before, code_after, patch_diff, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                """, (
                    run_id,
                    item.get("file_path", "unknown"),
                    item.get("target_symbol", ""),
                    item.get("issue_type", "API_MISMATCH"),
                    item.get("human_action", "Apply suggested modification"),
                    item.get("code_before", ""),
                    item.get("code_after", ""),
                    item.get("patch_diff", ""),
                ))

            conn.commit()
            return run_id

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM audit_runs ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM remediation_tasks WHERE run_id = ? ORDER BY id ASC
            """, (run_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_database_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM audit_runs")
            total_runs = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM remediation_tasks")
            total_tasks = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM audit_runs WHERE decision = 'PASSED'")
            passed_runs = cursor.fetchone()["total"]

            return {
                "db_file": str(self.db_path),
                "total_runs": total_runs,
                "total_remediation_tasks": total_tasks,
                "passed_runs": passed_runs,
                "blocked_runs": total_runs - passed_runs,
            }
