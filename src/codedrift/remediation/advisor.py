"""
Remediation Advisor & Action Synthesizer for CodeDrift.
Translates technical diffs and blast radius call sites into plain-English developer action items.
"""
from typing import List, Dict, Any, Optional
from ..core.models import BlastRadiusReport, RemediationPatch
from .patch_generator import PatchGenerator


class RemediationAdvisor:
    """
    Produces actionable remediation checklists and human-readable tasks
    telling developers exactly what needs to be changed and why.
    """

    def __init__(self, patcher: Optional[PatchGenerator] = None):
        self.patcher = patcher or PatchGenerator()

    def generate_plan(self, report: Optional[BlastRadiusReport], patches: List[RemediationPatch]) -> List[Dict[str, Any]]:
        """
        Builds a structured list of actionable remediation steps.
        """
        actions: List[Dict[str, Any]] = []

        if not report or not report.items:
            return actions

        patch_map = {p.file_path: p for p in patches}

        for item in report.items:
            if not item.is_reachable:
                continue

            change = item.change
            for cs in item.call_sites:
                file_name = cs.file_path.replace("\\", "/").split("/")[-1]
                target_sym = change.qualified_name
                change_type = change.change_type

                human_action = ""
                priority = "HIGH"

                if change_type == "PARAMETER_REMOVED":
                    param = change.parameter_name or "obsolete argument"
                    human_action = (
                        f"In {file_name} (line {cs.line}): Remove the '{param}' keyword argument from {target_sym}()."
                    )
                    priority = "CRITICAL"

                elif change_type in ("PARAMETER_ADDED_MANDATORY", "PARAMETER_ADDED_REQUIRED"):
                    param = change.parameter_name or "mandatory argument"
                    human_action = (
                        f"In {file_name} (line {cs.line}): Provide the newly required '{param}' argument when calling {target_sym}()."
                    )
                    priority = "CRITICAL"

                elif change_type == "RETURN_TYPE_CHANGED":
                    old_t = getattr(change, "old_value", None) or getattr(change, "old_val", "previous type")
                    new_t = getattr(change, "new_value", None) or getattr(change, "new_val", "new type")
                    human_action = (
                        f"In {file_name} (line {cs.line}): {target_sym}() now returns {new_t} instead of {old_t}. Update callers to handle the new return data structure."
                    )
                    priority = "HIGH"

                elif change_type == "FUNCTION_REMOVED":
                    human_action = (
                        f"In {file_name} (line {cs.line}): Function {target_sym}() was deleted in the library. Replace it with its official migration alternative."
                    )
                    priority = "CRITICAL"

                else:
                    human_action = f"In {file_name} (line {cs.line}): Update usage to match signature of {target_sym}()."
                    priority = "MEDIUM"

                associated_patch = patch_map.get(cs.file_path)

                actions.append({
                    "file_path": cs.file_path,
                    "file_name": file_name,
                    "line": cs.line,
                    "target_symbol": target_sym,
                    "issue_type": change_type,
                    "priority": priority,
                    "human_action": human_action,
                    "caller_snippet": cs.code_snippet,
                    "code_before": associated_patch.original_code if associated_patch else cs.code_snippet,
                    "code_after": associated_patch.patched_code if associated_patch else "",
                    "patch_diff": associated_patch.diff if associated_patch else "",
                    "status": "ACTION_REQUIRED"
                })

        return actions
