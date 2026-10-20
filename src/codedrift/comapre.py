"""
Comparison script facade (retained for backward compatibility).
For the modern CLI, use `python -m codedrift diff <old_file> <new_file>` or `codedrift diff`.
"""
from typing import Dict, Any
try:
    from .parser import PythonParser
    from .detection import DiffEngine
except ImportError:
    from codedrift.parser import PythonParser
    from codedrift.detection import DiffEngine


def compare_versions(
    old_file: str,
    new_file: str,
) -> Dict[str, Any]:
    parser = PythonParser()
    old_api = parser.parse_file(old_file)
    new_api = parser.parse_file(new_file)

    engine = DiffEngine()
    result = engine.compare(
        old_module=old_api,
        new_module=new_api,
    )

    return result.to_dict()


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        old_f, new_f = sys.argv[1], sys.argv[2]
    else:
        old_f = "data/fixtures/v1/payment_gateway.py"
        new_f = "data/fixtures/v2/payment_gateway.py"

    try:
        result = compare_versions(old_f, new_f)
        for change in result["changes"]:
            print(f"{change['severity']}: {change['change_type']} - {change['description']}")
    except Exception as e:
        print(f"Error comparing versions: {e}")