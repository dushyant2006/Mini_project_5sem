import ast


def extract_functions(file_path):
    with open(file_path, "r") as file:
        code = file.read()

    tree = ast.parse(code)

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return functions