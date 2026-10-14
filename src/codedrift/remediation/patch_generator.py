"""
Autonomous Remediation and Codemod Patch Generator.
Generates unified diffs and AST transformations to automatically adapt downstream call-sites
to upstream breaking changes.
"""
import difflib
import re
from pathlib import Path
from typing import List, Optional
from ..core.models import BlastRadiusReport, RemediationPatch


class PatchGenerator:
    """
    Synthesizes automated diff patches to update client call sites.
    """

    def generate_patches(self, report: BlastRadiusReport) -> List[RemediationPatch]:
        patches: List[RemediationPatch] = []

        # Group reachable items by affected file
        file_to_items = {}
        for item in report.items:
            if not item.is_reachable:
                continue
            for cs in item.call_sites:
                file_to_items.setdefault(cs.file_path, []).append((item.change, cs))

        for file_path, changes_with_sites in file_to_items.items():
            path = Path(file_path)
            if not path.is_file():
                continue

            try:
                original_content = path.read_text(encoding="utf-8")
            except Exception:
                continue

            lines = original_content.splitlines(keepends=True)
            modified_lines = list(lines)

            # Apply line-level transformations
            for change, cs in changes_with_sites:
                line_idx = cs.line - 1
                if 0 <= line_idx < len(modified_lines):
                    old_line = modified_lines[line_idx]
                    new_line = self._transform_line(old_line, change, cs)
                    if new_line != old_line:
                        modified_lines[line_idx] = new_line

            patched_content = "".join(modified_lines)
            if patched_content != original_content:
                diff = "".join(
                    difflib.unified_diff(
                        original_content.splitlines(keepends=True),
                        patched_content.splitlines(keepends=True),
                        fromfile=f"a/{path.name}",
                        tofile=f"b/{path.name}",
                    )
                )
                patches.append(
                    RemediationPatch(
                        file_path=file_path,
                        original_code=original_content,
                        patched_code=patched_content,
                        diff=diff,
                        target_symbol=changes_with_sites[0][0].qualified_name,
                        reason=f"Auto-repair {len(changes_with_sites)} breaking call site(s)",
                    )
                )

        return patches

    def _transform_line(self, line: str, change, call_site) -> str:
        """
        Applies targeted replacement for common breaking patterns.
        """
        # If parameter was removed, strip that keyword argument
        if change.change_type == "PARAMETER_REMOVED" and change.parameter_name:
            pname = change.parameter_name
            # Replace ", pname=val" or "pname=val, " or "pname=val"
            pattern1 = rf",\s*{pname}\s*=\s*[^,\)]+"
            pattern2 = rf"{pname}\s*=\s*[^,\)]+,\s*"
            pattern3 = rf"{pname}\s*=\s*[^,\)]+"
            new_line = re.sub(pattern1, "", line)
            new_line = re.sub(pattern2, "", new_line)
            new_line = re.sub(pattern3, "", new_line)
            return new_line

        return line
