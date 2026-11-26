import json
import os
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ScanStore:

    def __init__(self, directory=None):

        default_directory = (
            Path.home() / ".codedrift" / "scans"
        )

        self.directory = Path(
            directory
            or os.getenv("CODEDRIFT_SCAN_DIR")
            or default_directory
        )

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.lock = RLock()

    def get_path(self, scan_id):

        safe_id = str(UUID(str(scan_id)))

        return self.directory / f"{safe_id}.json"

    def save(self, record):

        with self.lock:

            path = self.get_path(record["id"])

            temporary_path = None

            try:

                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.directory,
                    suffix=".tmp",
                    delete=False,
                ) as temporary:

                    temporary_path = Path(
                        temporary.name
                    )

                    json.dump(
                        record,
                        temporary,
                        indent=2,
                        ensure_ascii=False,
                    )

                os.replace(
                    temporary_path,
                    path,
                )

            finally:

                if temporary_path:

                    temporary_path.unlink(
                        missing_ok=True
                    )

        return record

    def create(
        self,
        repository_url,
        offline=False,
        max_comparisons=5,
    ):

        record = {
            "id": str(uuid4()),
            "repository_url": repository_url,
            "status": "queued",
            "created_at": utc_now(),
            "started_at": None,
            "completed_at": None,
            "offline": offline,
            "max_comparisons": max_comparisons,
            "error": None,
            "report": None,
        }

        return self.save(record)

    def get(self, scan_id):

        with self.lock:

            path = self.get_path(scan_id)

            if not path.exists():
                return None

            return json.loads(
                path.read_text(encoding="utf-8")
            )

    def update(self, scan_id, **fields):

        with self.lock:

            record = self.get(scan_id)

            if record is None:
                raise KeyError(scan_id)

            record.update(fields)

            return self.save(record)

    def list_scans(self):

        with self.lock:

            records = []

            for path in self.directory.glob("*.json"):

                record = json.loads(
                    path.read_text(encoding="utf-8")
                )

                report = record.pop("report", None)

                if report:

                    record["summary"] = {
                        "dependency_count": report.get(
                            "dependency_count", 0
                        ),
                        "updates_found": report.get(
                            "updates_found", 0
                        ),
                        "vulnerable_dependencies": report.get(
                            "vulnerable_dependencies", 0
                        ),
                        "impact_analysis": report.get(
                            "impact_analysis", {}
                        ).get(
                            "highest_dependency_impact_score"
                        ),
                    }

                else:

                    record["summary"] = None

                records.append(record)

            return sorted(
                records,
                key=lambda item: item["created_at"],
                reverse=True,
            )

    def delete(self, scan_id):

        with self.lock:

            record = self.get(scan_id)

            if record is None:
                return False

            if record["status"] in {
                "queued", "running"
            }:

                raise ValueError(
                    "An active scan cannot be deleted."
                )

            self.get_path(scan_id).unlink()

            return True

    def recover_interrupted_scans(self):

        with self.lock:

            for record in self.list_scans():

                if record["status"] in {
                    "queued", "running"
                }:

                    self.update(
                        record["id"],
                        status="failed",
                        completed_at=utc_now(),
                        error="Scan interrupted by server shutdown.",
                    )