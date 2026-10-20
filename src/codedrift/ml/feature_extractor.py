"""
Feature Extraction Engine for Dependency Degradation Prediction.
Extracts structural, semantic, and invocation features from API diffs and call-graphs.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from ..core.models import DiffResult, BlastRadiusReport


@dataclass
class DegradationFeatures:
    total_changes: int
    breaking_changes: int
    breaking_ratio: float
    critical_count: int
    high_count: int
    reachable_breaking_count: int
    reachability_ratio: float
    blast_radius_score: float
    affected_files_count: int
    call_sites_density: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_vector(self) -> list[float]:
        return [
            float(self.total_changes),
            float(self.breaking_changes),
            self.breaking_ratio,
            float(self.critical_count),
            float(self.high_count),
            float(self.reachable_breaking_count),
            self.reachability_ratio,
            self.blast_radius_score,
            float(self.affected_files_count),
            self.call_sites_density,
        ]


class DegradationFeatureExtractor:
    """
    Transforms API diffs and client reachability reports into numerical feature vectors.
    """

    def extract(
        self,
        diff_result: DiffResult,
        blast_report: Optional[BlastRadiusReport] = None,
    ) -> DegradationFeatures:
        total = max(1, len(diff_result.changes))
        breaking = len(diff_result.breaking_changes)
        breaking_ratio = round(breaking / total, 3)

        critical_count = sum(1 for c in diff_result.changes if c.severity == "CRITICAL")
        high_count = sum(1 for c in diff_result.changes if c.severity == "HIGH")

        reachable = 0
        reachability_ratio = 0.0
        blast_score = 0.0
        affected_files = 0
        call_density = 0.0

        if blast_report is not None:
            reachable = blast_report.reachable_breaking_count
            reachability_ratio = round(reachable / max(1, breaking), 3) if breaking > 0 else 0.0
            blast_score = blast_report.blast_radius_score
            affected_files = len(blast_report.affected_files)
            total_sites = sum(len(it.call_sites) for it in blast_report.items if it.is_reachable)
            call_density = round(total_sites / max(1, affected_files), 2)

        return DegradationFeatures(
            total_changes=len(diff_result.changes),
            breaking_changes=breaking,
            breaking_ratio=breaking_ratio,
            critical_count=critical_count,
            high_count=high_count,
            reachable_breaking_count=reachable,
            reachability_ratio=reachability_ratio,
            blast_radius_score=blast_score,
            affected_files_count=affected_files,
            call_sites_density=call_density,
        )
