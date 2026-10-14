"""
Blast Radius and Reachability Impact Analyzer.
Intersects upstream breaking API changes with downstream client call graphs to calculate
exact affected call-sites and normalized blast-radius risk scores.
"""
import math
from pathlib import Path
from typing import List, Optional, Set, Union
from ..core.models import (
    APIChange,
    BlastRadiusItem,
    BlastRadiusReport,
    CallSite,
    DiffResult,
)
from ..core.enums import Severity
from .callgraph import CallGraphBuilder


class BlastRadiusAnalyzer:
    """
    Computes reachability and blast radius for a given API diff against a consumer codebase.
    """

    def __init__(self, builder: Optional[CallGraphBuilder] = None):
        self.builder = builder or CallGraphBuilder()

    def analyze(
        self,
        diff_result: DiffResult,
        client_dir: Union[str, Path],
        target_package_name: Optional[str] = None,
    ) -> BlastRadiusReport:
        client_path = Path(client_dir)
        call_sites = self.builder.scan_directory(client_path)

        items: List[BlastRadiusItem] = []
        affected_files_set: Set[str] = set()

        # Filter to breaking changes only
        breaking_changes = diff_result.breaking_changes

        total_weighted_risk = 0.0

        for change in breaking_changes:
            matching_sites = self._find_matching_call_sites(change, call_sites, target_package_name)
            is_reachable = len(matching_sites) > 0

            # Calculate item impact score: severity_weight * ln(1 + call_sites_count)
            sev_enum = getattr(Severity, change.severity, Severity.MEDIUM)
            weight = sev_enum.weight if hasattr(sev_enum, "weight") else 0.5
            
            item_score = 0.0
            if is_reachable:
                # Logarithmic growth based on number of active call sites
                item_score = weight * (1.0 + math.log(1 + len(matching_sites)))
                total_weighted_risk += item_score
                for cs in matching_sites:
                    affected_files_set.add(cs.file_path)

            items.append(
                BlastRadiusItem(
                    change=change,
                    call_sites=matching_sites,
                    is_reachable=is_reachable,
                    impact_score=round(item_score, 2),
                )
            )

        reachable_count = sum(1 for item in items if item.is_reachable)

        # Normalize score to 0 - 100
        # If no reachable breaks exist, score is 0.0 (safe to auto-merge!)
        if reachable_count == 0:
            normalized_score = 0.0
        else:
            # Baseline sigmoid-like scaling
            normalized_score = min(100.0, total_weighted_risk * 25.0)

        return BlastRadiusReport(
            client_dir=str(client_path),
            total_breaking_upstream=len(breaking_changes),
            reachable_breaking_count=reachable_count,
            blast_radius_score=round(normalized_score, 2),
            items=items,
            affected_files=sorted(list(affected_files_set)),
        )

    def _find_matching_call_sites(
        self,
        change: APIChange,
        call_sites: List[CallSite],
        target_package_name: Optional[str] = None,
    ) -> List[CallSite]:
        """
        Determines which client call sites invoke the breaking symbol.
        """
        matches: List[CallSite] = []
        qname = change.qualified_name
        symbol_leaf = qname.split(".")[-1]

        for site in call_sites:
            target = site.matched_target
            callee = site.callee_name

            # Direct match on qualified target or callee
            is_direct_match = (
                target == qname or
                callee == qname or
                callee.endswith(f".{symbol_leaf}") or
                callee == symbol_leaf
            )

            # If target_package_name is provided, filter out other modules
            if target_package_name and is_direct_match:
                if site.matched_target and not site.matched_target.startswith(target_package_name):
                    continue

            if not is_direct_match:
                continue

            # Detailed check for removed parameters
            if change.change_type == "PARAMETER_REMOVED" and change.parameter_name:
                param_name = change.parameter_name
                # Check if client explicitly passes this argument
                passes_param = any(
                    arg.startswith(f"{param_name}=") or arg == param_name
                    for arg in site.arguments_passed
                )
                if passes_param:
                    matches.append(site)
                elif not site.arguments_passed:
                    # If no args were passed or positional, keep candidate
                    matches.append(site)
            else:
                matches.append(site)

        return matches
