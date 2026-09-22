from src.codedrift.parser import PythonParser
from src.codedrift.detection import DiffEngine


def compare_versions(
    old_file: str,
    new_file: str,
) -> dict:

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

    result = compare_versions(
        "data/old_version/paymentlib.py",
        "data/new_version/paymentlib.py",
    )

    for change in result["changes"]:
        print(
            f"{change['severity']}: "
            f"{change['change_type']} - "
            f"{change['description']}"
        )