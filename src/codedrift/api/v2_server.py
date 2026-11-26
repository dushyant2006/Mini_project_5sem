
import logging

from contextlib import asynccontextmanager
from threading import RLock
from uuid import UUID

from fastapi import (
    FastAPI,
    BackgroundTasks,
    HTTPException,
    Query,
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field

from codedrift.api.scan_store import (
    ScanStore,
    utc_now,
)

from codedrift.repository.github_client import (
    validate_github_url,
    RepositoryError,
)

from codedrift.repository.full_analyzer import (
    analyze_full_github_repository,
)


logger = logging.getLogger(__name__)

MAX_ACTIVE_SCANS = 2


class AnalyzeRequest(BaseModel):

    repository_url: str = Field(
        min_length=10,
        max_length=500,
    )

    offline: bool = False

    max_comparisons: int = Field(
        default=5,
        ge=0,
        le=20,
    )


def execute_scan(store, scan_id):

    try:

        record = store.update(
            scan_id,
            status="running",
            started_at=utc_now(),
        )

        report = analyze_full_github_repository(
            record["repository_url"],
            offline=record["offline"],
            max_comparisons=record[
                "max_comparisons"
            ],
        )

        store.update(
            scan_id,
            status="completed",
            completed_at=utc_now(),
            report=report,
            error=None,
        )

    except Exception:

        logger.exception(
            "Repository scan failed: %s",
            scan_id,
        )

        store.update(
            scan_id,
            status="failed",
            completed_at=utc_now(),
            error=(
                "Repository analysis failed. "
                "Check the backend logs."
            ),
        )


def create_app(storage_directory=None):

    store = ScanStore(storage_directory)

    submission_lock = RLock()

    @asynccontextmanager
    async def lifespan(application):

        store.recover_interrupted_scans()

        yield

    app = FastAPI(
        title="CodeDrift API",
        description=(
            "Autonomous API Breaking-Change "
            "and Dependency Degradation Guard"
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    app.state.scan_store = store

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "DELETE",
        ],
        allow_headers=["Content-Type"],
    )

    def get_scan_or_404(scan_id):

        record = store.get(scan_id)

        if record is None:

            raise HTTPException(
                status_code=404,
                detail="Scan not found.",
            )

        return record

    def get_completed_report(scan_id):

        record = get_scan_or_404(scan_id)

        if record["status"] != "completed":

            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Scan is not completed.",
                    "status": record["status"],
                },
            )

        return record["report"]

    @app.get("/")
    def root():

        return {
            "service": "CodeDrift",
            "api_version": "2.0.0",
            "documentation": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    @app.get("/api/v2/health")
    def health():

        return {
            "status": "healthy",
            "service": "CodeDrift API",
            "version": "2.0.0",
            "storage": "json",
        }

    @app.post(
        "/api/v2/analyze",
        status_code=202,
    )
    def start_analysis(
        request: AnalyzeRequest,
        background_tasks: BackgroundTasks,
    ):

        try:

            repository_url = validate_github_url(
                request.repository_url
            )

        except (RepositoryError, ValueError):

            raise HTTPException(
                status_code=422,
                detail="Invalid public GitHub repository URL.",
            )

        with submission_lock:

            active_scans = sum(
                record["status"] in {
                    "queued", "running"
                }
                for record in store.list_scans()
            )

            if active_scans >= MAX_ACTIVE_SCANS:

                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Maximum active scans reached. "
                        "Please try again later."
                    ),
                )

            record = store.create(
                repository_url=repository_url,
                offline=request.offline,
                max_comparisons=request.max_comparisons,
            )

            background_tasks.add_task(
                execute_scan,
                store,
                record["id"],
            )

        return {
            "scan_id": record["id"],
            "repository_url": repository_url,
            "status": "queued",
            "status_url": (
                f"/api/v2/scans/{record['id']}"
            ),
        }

    @app.get("/api/v2/scans")
    def list_scans(
        limit: int = Query(
            default=20,
            ge=1,
            le=100,
        ),
        offset: int = Query(
            default=0,
            ge=0,
        ),
    ):

        scans = store.list_scans()

        return {
            "total": len(scans),
            "limit": limit,
            "offset": offset,
            "scans": scans[offset:offset + limit],
        }

    @app.get("/api/v2/scans/{scan_id}")
    def get_scan(scan_id: UUID):

        return get_scan_or_404(scan_id)

    @app.get(
        "/api/v2/scans/{scan_id}/dependencies"
    )
    def get_dependencies(
        scan_id: UUID,
        ecosystem: str | None = None,
        updates_only: bool = False,
    ):

        report = get_completed_report(scan_id)

        dependencies = report.get(
            "dependencies", []
        )

        if ecosystem:

            dependencies = [
                dependency
                for dependency in dependencies
                if dependency.get("ecosystem")
                == ecosystem.lower()
            ]

        if updates_only:

            dependencies = [
                dependency
                for dependency in dependencies
                if dependency.get("comparison_status")
                == "update_available"
            ]

        return {
            "scan_id": str(scan_id),
            "dependency_count": len(dependencies),
            "dependencies": dependencies,
        }

    @app.get(
        "/api/v2/scans/{scan_id}/security"
    )
    def get_security(scan_id: UUID):

        report = get_completed_report(scan_id)

        vulnerable = []

        for dependency in report.get(
            "dependencies", []
        ):

            if dependency.get(
                "security_status"
            ) == "vulnerable":

                vulnerable.append({
                    "name": dependency["name"],
                    "ecosystem": dependency["ecosystem"],
                    "baseline_version": dependency.get(
                        "baseline_version"
                    ),
                    "vulnerability_count": dependency.get(
                        "vulnerability_count"
                    ),
                    "vulnerabilities": dependency.get(
                        "vulnerabilities", []
                    ),
                })

        return {
            "scan_id": str(scan_id),
            "vulnerable_dependencies": report.get(
                "vulnerable_dependencies", 0
            ),
            "vulnerabilities_found": report.get(
                "vulnerabilities_found", 0
            ),
            "unique_advisory_count": report.get(
                "unique_advisory_count", 0
            ),
            "unique_cve_count": report.get(
                "unique_cve_count", 0
            ),
            "unique_cve_ids": report.get(
                "unique_cve_ids", []
            ),
            "security_checked": report.get(
                "security_checked", 0
            ),
            "security_unchecked": report.get(
                "security_unchecked", 0
            ),
            "security_lookup_failures": report.get(
                "security_lookup_failures", 0
            ),
            "dependencies": vulnerable,
        }

    @app.get(
        "/api/v2/scans/{scan_id}/breaking-changes"
    )
    def get_breaking_changes(scan_id: UUID):

        report = get_completed_report(scan_id)

        comparisons = []

        for dependency in report.get(
            "dependencies", []
        ):

            comparisons.append({
                "name": dependency["name"],
                "baseline_version": dependency.get(
                    "baseline_version"
                ),
                "candidate_version": dependency.get(
                    "latest_release"
                ),
                "status": dependency.get(
                    "api_analysis_status"
                ),
                "breaking_count": dependency.get(
                    "api_breaking_count"
                ),
                "comparison": dependency.get(
                    "api_comparison"
                ),
                "error": dependency.get(
                    "api_analysis_error"
                ),
            })

        return {
            "scan_id": str(scan_id),
            "summary": report.get(
                "api_analysis", {}
            ),
            "comparisons": comparisons,
        }

    @app.get(
        "/api/v2/scans/{scan_id}/impact"
    )
    def get_impact(scan_id: UUID):

        report = get_completed_report(scan_id)

        dependencies = []

        for dependency in report.get(
            "dependencies", []
        ):

            dependencies.append({
                "name": dependency["name"],
                "baseline_version": dependency.get(
                    "baseline_version"
                ),
                "candidate_version": dependency.get(
                    "latest_release"
                ),
                "status": dependency.get(
                    "impact_analysis_status"
                ),
                "impact_score": dependency.get(
                    "impact_score"
                ),
                "risk_level": dependency.get(
                    "risk_level", "UNKNOWN"
                ),
                "impact_report": dependency.get(
                    "impact_report"
                ),
            })

        return {
            "scan_id": str(scan_id),
            "summary": report.get(
                "impact_analysis", {}
            ),
            "dependencies": dependencies,
        }

    @app.delete("/api/v2/scans/{scan_id}")
    def delete_scan(scan_id: UUID):

        try:

            deleted = store.delete(scan_id)

        except ValueError as error:

            raise HTTPException(
                status_code=409,
                detail=str(error),
            )

        if not deleted:

            raise HTTPException(
                status_code=404,
                detail="Scan not found.",
            )

        return {
            "scan_id": str(scan_id),
            "deleted": True,
        }

    return app


app = create_app()
