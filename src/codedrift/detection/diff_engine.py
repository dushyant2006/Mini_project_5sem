"""
Semantic Diff and Breaking Change Detection Engine.
Compares two AST module representations or packages to identify API contract shifts,
breaking changes, deprecations, and parameter modifications.
"""
from typing import Dict, List, Optional, Set, Union
from ..core.models import (
    APIChange,
    ClassInfo,
    DiffResult,
    FunctionInfo,
    ModuleInfo,
    ParameterInfo,
)
from ..core.enums import ChangeType, Severity


class DiffEngine:
    """
    Compares two versions of an API to identify breaking and non-breaking contract changes.
    """

    def compare(
        self,
        old_module: ModuleInfo,
        new_module: ModuleInfo,
    ) -> DiffResult:
        changes: List[APIChange] = []

        changes.extend(
            self._compare_functions(
                old_module.functions,
                new_module.functions,
            )
        )

        changes.extend(
            self._compare_classes(
                old_module.classes,
                new_module.classes,
            )
        )

        return DiffResult(
            changes=changes,
            old_module_name=old_module.module_name,
            new_module_name=new_module.module_name,
        )

    def compare_packages(
        self,
        old_modules: List[ModuleInfo],
        new_modules: List[ModuleInfo],
    ) -> DiffResult:
        """
        Compares an entire package (multiple modules).
        """
        all_changes: List[APIChange] = []
        old_map: Dict[str, ModuleInfo] = {m.module_name: m for m in old_modules}
        new_map: Dict[str, ModuleInfo] = {m.module_name: m for m in new_modules}

        # Check removed modules
        for mod_name, old_m in old_map.items():
            if mod_name not in new_map:
                all_changes.append(
                    APIChange(
                        change_type="MODULE_REMOVED",
                        qualified_name=mod_name,
                        old_value=old_m.file_path,
                        severity=Severity.CRITICAL.value,
                        is_breaking=True,
                        description=f"Module '{mod_name}' was removed from package.",
                        suggested_migration=f"Stop importing from '{mod_name}' or update to replacement module.",
                    )
                )

        # Check added modules
        for mod_name, new_m in new_map.items():
            if mod_name not in old_map:
                all_changes.append(
                    APIChange(
                        change_type="MODULE_ADDED",
                        qualified_name=mod_name,
                        new_value=new_m.file_path,
                        severity=Severity.LOW.value,
                        is_breaking=False,
                        description=f"New module '{mod_name}' was added to package.",
                    )
                )

        # Compare matching modules
        for mod_name in old_map.keys() & new_map.keys():
            diff = self.compare(old_map[mod_name], new_map[mod_name])
            all_changes.extend(diff.changes)

        return DiffResult(changes=all_changes)

    # --------------------------------------------------
    # FUNCTIONS
    # --------------------------------------------------

    def _compare_functions(
        self,
        old_functions: List[FunctionInfo],
        new_functions: List[FunctionInfo],
    ) -> List[APIChange]:
        changes: List[APIChange] = []

        old_map = {f.qualified_name: f for f in old_functions}
        new_map = {f.qualified_name: f for f in new_functions}

        # Function removed
        for name, old_fn in old_map.items():
            if name not in new_map:
                changes.append(
                    APIChange(
                        change_type=ChangeType.FUNCTION_REMOVED.value,
                        qualified_name=name,
                        old_value=old_fn.signature,
                        severity=Severity.CRITICAL.value,
                        is_breaking=True,
                        description=f"Public function '{name}' was removed.",
                        suggested_migration=f"Check upstream changelog for replacement of '{name}'.",
                    )
                )

        # Function added
        for name, new_fn in new_map.items():
            if name not in old_map:
                changes.append(
                    APIChange(
                        change_type=ChangeType.FUNCTION_ADDED.value,
                        qualified_name=name,
                        new_value=new_fn.signature,
                        severity=Severity.LOW.value,
                        is_breaking=False,
                        description=f"New function '{name}' was added.",
                    )
                )

        # Compare functions existing in both
        for name in old_map.keys() & new_map.keys():
            changes.extend(
                self._compare_function_details(old_map[name], new_map[name])
            )

        return changes

    def _compare_function_details(
        self,
        old_fn: FunctionInfo,
        new_fn: FunctionInfo,
    ) -> List[APIChange]:
        changes: List[APIChange] = []

        # Visibility reduced
        if old_fn.visibility == "public" and new_fn.visibility != "public":
            changes.append(
                APIChange(
                    change_type="VISIBILITY_REDUCED",
                    qualified_name=old_fn.qualified_name,
                    old_value=old_fn.visibility,
                    new_value=new_fn.visibility,
                    severity=Severity.CRITICAL.value,
                    is_breaking=True,
                    description=f"Function '{old_fn.qualified_name}' changed from public to {new_fn.visibility}.",
                    suggested_migration=f"Avoid calling private internal function '{old_fn.qualified_name}'.",
                )
            )

        # Return type change
        if old_fn.return_type != new_fn.return_type:
            changes.append(
                APIChange(
                    change_type=ChangeType.RETURN_TYPE_CHANGED.value,
                    qualified_name=old_fn.qualified_name,
                    old_value=old_fn.return_type,
                    new_value=new_fn.return_type,
                    severity=Severity.HIGH.value,
                    is_breaking=True,
                    description=f"Return type changed from '{old_fn.return_type}' to '{new_fn.return_type}'.",
                    suggested_migration=f"Update callers to handle returned '{new_fn.return_type}'.",
                )
            )

        # Parameters
        changes.extend(self._compare_parameters(old_fn, new_fn))

        # Async status
        if old_fn.is_async != new_fn.is_async:
            changes.append(
                APIChange(
                    change_type=ChangeType.ASYNC_STATUS_CHANGED.value,
                    qualified_name=old_fn.qualified_name,
                    old_value=str(old_fn.is_async),
                    new_value=str(new_fn.is_async),
                    severity=Severity.CRITICAL.value,
                    is_breaking=True,
                    description=f"Async status changed for '{old_fn.qualified_name}' (is_async={new_fn.is_async}).",
                    suggested_migration=f"{'Await' if new_fn.is_async else 'Remove await from'} calls to '{old_fn.qualified_name}'.",
                )
            )

        # Decorators / Deprecations
        old_decs = set(old_fn.decorators)
        new_decs = set(new_fn.decorators)
        added_decs = new_decs - old_decs
        for dec in added_decs:
            if "deprecated" in dec.lower():
                changes.append(
                    APIChange(
                        change_type=ChangeType.DEPRECATION_ADDED.value,
                        qualified_name=old_fn.qualified_name,
                        new_value=dec,
                        severity=Severity.MEDIUM.value,
                        is_breaking=False,
                        description=f"Function '{old_fn.qualified_name}' is now deprecated: @{dec}.",
                        suggested_migration=f"Plan migration away from deprecated function '{old_fn.qualified_name}'.",
                    )
                )

        # Raised exceptions
        if old_fn.raises != new_fn.raises:
            new_exceptions = set(new_fn.raises) - set(old_fn.raises)
            if new_exceptions:
                changes.append(
                    APIChange(
                        change_type=ChangeType.EXCEPTION_RAISED_CHANGED.value,
                        qualified_name=old_fn.qualified_name,
                        old_value=", ".join(old_fn.raises),
                        new_value=", ".join(new_fn.raises),
                        severity=Severity.MEDIUM.value,
                        is_breaking=False,
                        description=f"New exceptions raised by '{old_fn.qualified_name}': {', '.join(new_exceptions)}.",
                        suggested_migration=f"Wrap call sites with try/except ({', '.join(new_exceptions)}).",
                    )
                )

        return changes

    # --------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------

    def _compare_parameters(
        self,
        old_fn: FunctionInfo,
        new_fn: FunctionInfo,
    ) -> List[APIChange]:
        changes: List[APIChange] = []

        old_params = {p.name: p for p in old_fn.parameters}
        new_params = {p.name: p for p in new_fn.parameters}

        # Removed parameters
        for name in old_params:
            if name not in new_params:
                changes.append(
                    APIChange(
                        change_type=ChangeType.PARAMETER_REMOVED.value,
                        qualified_name=old_fn.qualified_name,
                        parameter_name=name,
                        old_value=self._parameter_string(old_params[name]),
                        severity=Severity.HIGH.value,
                        is_breaking=True,
                        description=f"Parameter '{name}' was removed from '{old_fn.qualified_name}'.",
                        suggested_migration=f"Remove '{name}' argument from all call sites of '{old_fn.name}'.",
                    )
                )

        # Added parameters
        for name, new_p in new_params.items():
            if name not in old_params:
                is_mandatory = new_p.default is None and new_p.kind not in ("var_positional", "var_keyword")
                severity = Severity.HIGH.value if is_mandatory else Severity.LOW.value
                change_type = (
                    ChangeType.PARAMETER_ADDED_MANDATORY.value
                    if is_mandatory
                    else ChangeType.PARAMETER_ADDED_OPTIONAL.value
                )

                changes.append(
                    APIChange(
                        change_type=change_type,
                        qualified_name=old_fn.qualified_name,
                        parameter_name=name,
                        new_value=self._parameter_string(new_p),
                        severity=severity,
                        is_breaking=is_mandatory,
                        description=(
                            f"Mandatory parameter '{name}' added to '{old_fn.qualified_name}' without default."
                            if is_mandatory
                            else f"Optional parameter '{name}' added to '{old_fn.qualified_name}'."
                        ),
                        suggested_migration=(
                            f"Pass required '{name}' argument at all call sites."
                            if is_mandatory
                            else None
                        ),
                    )
                )

        # Existing parameters
        for name in old_params.keys() & new_params.keys():
            old_p = old_params[name]
            new_p = new_params[name]

            # Type annotation change
            if old_p.annotation != new_p.annotation and old_p.annotation is not None:
                changes.append(
                    APIChange(
                        change_type=ChangeType.PARAMETER_TYPE_CHANGED.value,
                        qualified_name=old_fn.qualified_name,
                        parameter_name=name,
                        old_value=old_p.annotation,
                        new_value=new_p.annotation,
                        severity=Severity.HIGH.value,
                        is_breaking=True,
                        description=f"Parameter '{name}' type changed from '{old_p.annotation}' to '{new_p.annotation}'.",
                        suggested_migration=f"Cast or convert '{name}' argument to '{new_p.annotation}'.",
                    )
                )

            # Default value removed (making it mandatory)
            if old_p.default is not None and new_p.default is None:
                changes.append(
                    APIChange(
                        change_type=ChangeType.PARAMETER_DEFAULT_CHANGED.value,
                        qualified_name=old_fn.qualified_name,
                        parameter_name=name,
                        old_value=old_p.default,
                        new_value=None,
                        severity=Severity.HIGH.value,
                        is_breaking=True,
                        description=f"Parameter '{name}' default '{old_p.default}' was removed, making it mandatory.",
                        suggested_migration=f"Explicitly pass '{name}' argument at all call sites.",
                    )
                )

        # Positional ordering check
        old_pos = [p.name for p in old_fn.parameters if p.kind in ("positional_only", "positional_or_keyword")]
        new_pos = [p.name for p in new_fn.parameters if p.kind in ("positional_only", "positional_or_keyword")]
        common_pos = [p for p in old_pos if p in new_pos]
        common_new_pos = [p for p in new_pos if p in old_pos]

        if common_pos != common_new_pos:
            changes.append(
                APIChange(
                    change_type=ChangeType.PARAMETER_REORDERED.value,
                    qualified_name=old_fn.qualified_name,
                    old_value=", ".join(old_pos),
                    new_value=", ".join(new_pos),
                    severity=Severity.HIGH.value,
                    is_breaking=True,
                    description=f"Positional parameters for '{old_fn.qualified_name}' were reordered.",
                    suggested_migration=f"Use keyword arguments (e.g. {old_fn.name}(param=val)) to avoid positional mismatch.",
                )
            )

        return changes

    # --------------------------------------------------
    # CLASSES
    # --------------------------------------------------

    def _compare_classes(
        self,
        old_classes: List[ClassInfo],
        new_classes: List[ClassInfo],
    ) -> List[APIChange]:
        changes: List[APIChange] = []

        old_map = {c.qualified_name: c for c in old_classes}
        new_map = {c.qualified_name: c for c in new_classes}

        # Class removed
        for name, old_cls in old_map.items():
            if name not in new_map:
                changes.append(
                    APIChange(
                        change_type=ChangeType.CLASS_REMOVED.value,
                        qualified_name=name,
                        severity=Severity.CRITICAL.value,
                        is_breaking=True,
                        description=f"Class '{name}' was removed.",
                        suggested_migration=f"Check upstream release notes for replacement of '{name}'.",
                    )
                )

        # Class added
        for name, new_cls in new_map.items():
            if name not in old_map:
                changes.append(
                    APIChange(
                        change_type=ChangeType.CLASS_ADDED.value,
                        qualified_name=name,
                        severity=Severity.LOW.value,
                        is_breaking=False,
                        description=f"New class '{name}' was added.",
                    )
                )

        # Existing classes
        for name in old_map.keys() & new_map.keys():
            changes.extend(
                self._compare_class_details(old_map[name], new_map[name])
            )

        return changes

    def _compare_class_details(
        self,
        old_cls: ClassInfo,
        new_cls: ClassInfo,
    ) -> List[APIChange]:
        changes: List[APIChange] = []

        # Inheritance base changes
        if old_cls.bases != new_cls.bases:
            changes.append(
                APIChange(
                    change_type="INHERITANCE_CHANGED",
                    qualified_name=old_cls.qualified_name,
                    old_value=", ".join(old_cls.bases),
                    new_value=", ".join(new_cls.bases),
                    severity=Severity.HIGH.value,
                    is_breaking=True,
                    description=f"Base classes changed for '{old_cls.qualified_name}'.",
                )
            )

        # Methods
        old_methods = {m.qualified_name: m for m in old_cls.methods}
        new_methods = {m.qualified_name: m for m in new_cls.methods}

        for name, old_m in old_methods.items():
            if name not in new_methods:
                changes.append(
                    APIChange(
                        change_type=ChangeType.METHOD_REMOVED.value,
                        qualified_name=name,
                        old_value=old_m.signature,
                        severity=Severity.HIGH.value,
                        is_breaking=True,
                        description=f"Method '{name}' was removed.",
                        suggested_migration=f"Update callers to avoid calling removed method '{name}'.",
                    )
                )

        for name, new_m in new_methods.items():
            if name not in old_methods:
                changes.append(
                    APIChange(
                        change_type=ChangeType.METHOD_ADDED.value,
                        qualified_name=name,
                        new_value=new_m.signature,
                        severity=Severity.LOW.value,
                        is_breaking=False,
                        description=f"Method '{name}' was added.",
                    )
                )

        for name in old_methods.keys() & new_methods.keys():
            changes.extend(
                self._compare_function_details(old_methods[name], new_methods[name])
            )

        return changes

    @staticmethod
    def _parameter_string(parameter: ParameterInfo) -> str:
        value = parameter.name
        if parameter.annotation:
            value += f": {parameter.annotation}"
        if parameter.default is not None:
            value += f" = {parameter.default}"
        return value