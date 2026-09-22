from .models import APIChange, DiffResult
from ..parser.models import (
    ClassInfo,
    FunctionInfo,
    ModuleInfo,
    ParameterInfo,
)


class DiffEngine:

    def compare(
        self,
        old_module: ModuleInfo,
        new_module: ModuleInfo,
    ) -> DiffResult:

        changes = []

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

        return DiffResult(changes=changes)

    # --------------------------------------------------
    # FUNCTIONS
    # --------------------------------------------------

    def _compare_functions(
        self,
        old_functions: list[FunctionInfo],
        new_functions: list[FunctionInfo],
    ) -> list[APIChange]:

        changes = []

        old_map = {
            function.qualified_name: function
            for function in old_functions
        }

        new_map = {
            function.qualified_name: function
            for function in new_functions
        }

        # Function removed
        for name, old_function in old_map.items():

            if name not in new_map:

                changes.append(
                    APIChange(
                        change_type="FUNCTION_REMOVED",
                        qualified_name=name,
                        old_value=old_function.signature,
                        severity="HIGH",
                        description=(
                            f"Public function '{name}' "
                            "was removed."
                        ),
                    )
                )

        # Function added
        for name, new_function in new_map.items():

            if name not in old_map:

                changes.append(
                    APIChange(
                        change_type="FUNCTION_ADDED",
                        qualified_name=name,
                        new_value=new_function.signature,
                        severity="LOW",
                        description=(
                            f"New function '{name}' "
                            "was added."
                        ),
                    )
                )

        # Compare functions existing in both versions
        for name in old_map.keys() & new_map.keys():

            old_function = old_map[name]
            new_function = new_map[name]

            changes.extend(
                self._compare_function_details(
                    old_function,
                    new_function,
                )
            )

        return changes

    def _compare_function_details(
        self,
        old_function: FunctionInfo,
        new_function: FunctionInfo,
    ) -> list[APIChange]:

        changes = []

        # Visibility
        if old_function.visibility != new_function.visibility:

            if (
                old_function.visibility == "public"
                and new_function.visibility == "private"
            ):
                changes.append(
                    APIChange(
                        change_type="VISIBILITY_REDUCED",
                        qualified_name=old_function.qualified_name,
                        old_value=old_function.visibility,
                        new_value=new_function.visibility,
                        severity="CRITICAL",
                        description=(
                            f"Function '{old_function.qualified_name}' "
                            "changed from public to private."
                        ),
                    )
                )

        # Return type
        if old_function.return_type != new_function.return_type:

            changes.append(
                APIChange(
                    change_type="RETURN_TYPE_CHANGED",
                    qualified_name=old_function.qualified_name,
                    old_value=old_function.return_type,
                    new_value=new_function.return_type,
                    severity="HIGH",
                    description=(
                        f"Return type changed from "
                        f"'{old_function.return_type}' to "
                        f"'{new_function.return_type}'."
                    ),
                )
            )

        # Parameters
        changes.extend(
            self._compare_parameters(
                old_function,
                new_function,
            )
        )

        # Decorators
        if old_function.decorators != new_function.decorators:

            changes.append(
                APIChange(
                    change_type="DECORATORS_CHANGED",
                    qualified_name=old_function.qualified_name,
                    old_value=", ".join(
                        old_function.decorators
                    ),
                    new_value=", ".join(
                        new_function.decorators
                    ),
                    severity="MEDIUM",
                    description=(
                        f"Decorators changed for "
                        f"'{old_function.qualified_name}'."
                    ),
                )
            )

        # Exception behavior at API level
        if old_function.raises != new_function.raises:

            changes.append(
                APIChange(
                    change_type="EXCEPTION_CHANGED",
                    qualified_name=old_function.qualified_name,
                    old_value=", ".join(
                        old_function.raises
                    ),
                    new_value=", ".join(
                        new_function.raises
                    ),
                    severity="HIGH",
                    description=(
                        f"Raised exceptions changed for "
                        f"'{old_function.qualified_name}'."
                    ),
                )
            )

        # Async status
        if old_function.is_async != new_function.is_async:

            changes.append(
                APIChange(
                    change_type="ASYNC_STATUS_CHANGED",
                    qualified_name=old_function.qualified_name,
                    old_value=str(old_function.is_async),
                    new_value=str(new_function.is_async),
                    severity="HIGH",
                    description=(
                        f"Async status changed for "
                        f"'{old_function.qualified_name}'."
                    ),
                )
            )

        return changes

    # --------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------

    def _compare_parameters(
        self,
        old_function: FunctionInfo,
        new_function: FunctionInfo,
    ) -> list[APIChange]:

        changes = []

        old_parameters = {
            parameter.name: parameter
            for parameter in old_function.parameters
        }

        new_parameters = {
            parameter.name: parameter
            for parameter in new_function.parameters
        }

        # Removed parameters
        for name in old_parameters:

            if name not in new_parameters:

                changes.append(
                    APIChange(
                        change_type="PARAMETER_REMOVED",
                        qualified_name=old_function.qualified_name,
                        parameter_name=name,
                        old_value=self._parameter_string(
                            old_parameters[name]
                        ),
                        severity="HIGH",
                        description=(
                            f"Parameter '{name}' was removed "
                            f"from '{old_function.qualified_name}'."
                        ),
                    )
                )

        # Added parameters
        for name in new_parameters:

            if name not in old_parameters:

                new_parameter = new_parameters[name]

                # A required new parameter is more dangerous
                severity = (
                    "HIGH"
                    if new_parameter.default is None
                    else "MEDIUM"
                )

                changes.append(
                    APIChange(
                        change_type="PARAMETER_ADDED",
                        qualified_name=old_function.qualified_name,
                        parameter_name=name,
                        new_value=self._parameter_string(
                            new_parameter
                        ),
                        severity=severity,
                        description=(
                            f"Parameter '{name}' was added "
                            f"to '{old_function.qualified_name}'."
                        ),
                    )
                )

        # Parameters existing in both versions
        for name in old_parameters.keys() & new_parameters.keys():

            old_parameter = old_parameters[name]
            new_parameter = new_parameters[name]

            # Type/annotation change
            if (
                old_parameter.annotation
                != new_parameter.annotation
            ):
                changes.append(
                    APIChange(
                        change_type="PARAMETER_TYPE_CHANGED",
                        qualified_name=old_function.qualified_name,
                        parameter_name=name,
                        old_value=old_parameter.annotation,
                        new_value=new_parameter.annotation,
                        severity="HIGH",
                        description=(
                            f"Parameter '{name}' type changed "
                            f"from '{old_parameter.annotation}' "
                            f"to '{new_parameter.annotation}'."
                        ),
                    )
                )

            # Default value change
            if (
                old_parameter.default
                != new_parameter.default
            ):
                changes.append(
                    APIChange(
                        change_type="DEFAULT_VALUE_CHANGED",
                        qualified_name=old_function.qualified_name,
                        parameter_name=name,
                        old_value=old_parameter.default,
                        new_value=new_parameter.default,
                        severity="MEDIUM",
                        description=(
                            f"Default value for parameter "
                            f"'{name}' changed."
                        ),
                    )
                )

            # Parameter kind change
            if old_parameter.kind != new_parameter.kind:

                changes.append(
                    APIChange(
                        change_type="PARAMETER_KIND_CHANGED",
                        qualified_name=old_function.qualified_name,
                        parameter_name=name,
                        old_value=old_parameter.kind,
                        new_value=new_parameter.kind,
                        severity="HIGH",
                        description=(
                            f"Parameter '{name}' kind changed "
                            f"from '{old_parameter.kind}' "
                            f"to '{new_parameter.kind}'."
                        ),
                    )
                )

        return changes

    # --------------------------------------------------
    # CLASSES
    # --------------------------------------------------

    def _compare_classes(
        self,
        old_classes: list[ClassInfo],
        new_classes: list[ClassInfo],
    ) -> list[APIChange]:

        changes = []

        old_map = {
            class_info.qualified_name: class_info
            for class_info in old_classes
        }

        new_map = {
            class_info.qualified_name: class_info
            for class_info in new_classes
        }

        # Class removed
        for name, old_class in old_map.items():

            if name not in new_map:

                changes.append(
                    APIChange(
                        change_type="CLASS_REMOVED",
                        qualified_name=name,
                        severity="CRITICAL",
                        description=(
                            f"Class '{name}' was removed."
                        ),
                    )
                )

        # Class added
        for name, new_class in new_map.items():

            if name not in old_map:

                changes.append(
                    APIChange(
                        change_type="CLASS_ADDED",
                        qualified_name=name,
                        severity="LOW",
                        description=(
                            f"Class '{name}' was added."
                        ),
                    )
                )

        # Existing classes
        for name in old_map.keys() & new_map.keys():

            old_class = old_map[name]
            new_class = new_map[name]

            changes.extend(
                self._compare_class_details(
                    old_class,
                    new_class,
                )
            )

        return changes

    def _compare_class_details(
        self,
        old_class: ClassInfo,
        new_class: ClassInfo,
    ) -> list[APIChange]:

        changes = []

        # Base classes
        if old_class.bases != new_class.bases:

            changes.append(
                APIChange(
                    change_type="INHERITANCE_CHANGED",
                    qualified_name=old_class.qualified_name,
                    old_value=", ".join(old_class.bases),
                    new_value=", ".join(new_class.bases),
                    severity="HIGH",
                    description=(
                        f"Base classes changed for "
                        f"'{old_class.qualified_name}'."
                    ),
                )
            )

        # Visibility
        if old_class.visibility != new_class.visibility:

            changes.append(
                APIChange(
                    change_type="VISIBILITY_REDUCED",
                    qualified_name=old_class.qualified_name,
                    old_value=old_class.visibility,
                    new_value=new_class.visibility,
                    severity="CRITICAL",
                    description=(
                        f"Visibility changed for "
                        f"'{old_class.qualified_name}'."
                    ),
                )
            )

        # Methods
        old_methods = {
            method.qualified_name: method
            for method in old_class.methods
        }

        new_methods = {
            method.qualified_name: method
            for method in new_class.methods
        }

        for name, old_method in old_methods.items():

            if name not in new_methods:

                changes.append(
                    APIChange(
                        change_type="METHOD_REMOVED",
                        qualified_name=name,
                        old_value=old_method.signature,
                        severity="HIGH",
                        description=(
                            f"Method '{name}' was removed."
                        ),
                    )
                )

        for name in new_methods:

            if name not in old_methods:

                changes.append(
                    APIChange(
                        change_type="METHOD_ADDED",
                        qualified_name=name,
                        new_value=new_methods[name].signature,
                        severity="LOW",
                        description=(
                            f"Method '{name}' was added."
                        ),
                    )
                )

        for name in old_methods.keys() & new_methods.keys():

            changes.extend(
                self._compare_function_details(
                    old_methods[name],
                    new_methods[name],
                )
            )

        return changes

    @staticmethod
    def _parameter_string(
        parameter: ParameterInfo,
    ) -> str:

        value = parameter.name

        if parameter.annotation:
            value += f": {parameter.annotation}"

        if parameter.default is not None:
            value += f" = {parameter.default}"

        return value