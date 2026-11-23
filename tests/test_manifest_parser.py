
from codedrift.dependency.manifest_parser import (
    extract_dependencies,
    parse_requirements,
    parse_pyproject,
    parse_package_json,
    parse_pom_xml,
)


def test_python_requirements():
    content = """
requests==2.28.0
flask>=2.0
# Comment
"""

    deps, warnings = parse_requirements(
        content, "requirements.txt"
    )

    assert len(deps) == 2
    assert deps[0]["name"] == "requests"
    assert deps[0]["constraint"] == "==2.28.0"
    assert deps[1]["constraint"] == ">=2.0"
    assert warnings == []


def test_python_pyproject():
    content = """
[project]
name = "my-app"
dependencies = ["rich>=13.0", "requests==2.28.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
"""

    deps, warnings = parse_pyproject(
        content, "pyproject.toml"
    )

    assert len(deps) == 3
    assert deps[2]["group"] == "dev"
    assert warnings == []


def test_npm_dependencies():
    content = """
{
  "dependencies": {
    "react": "^18.2.0",
    "axios": "1.6.0"
  },
  "devDependencies": {
    "vite": "^5.0.0"
  }
}
"""

    deps, warnings = parse_package_json(
        content, "package.json"
    )

    assert len(deps) == 3
    assert deps[0]["name"] == "react"
    assert deps[0]["constraint"] == "^18.2.0"
    assert deps[2]["group"] == "development"
    assert warnings == []


def test_maven_dependencies():
    content = """
<project>
  <properties>
    <junit.version>5.10.0</junit.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>${junit.version}</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""

    deps, warnings = parse_pom_xml(
        content, "pom.xml"
    )

    assert len(deps) == 1
    assert deps[0]["name"] == (
        "org.junit.jupiter:junit-jupiter"
    )
    assert deps[0]["constraint"] == "5.10.0"
    assert deps[0]["group"] == "test"
    assert warnings == []


def test_unsupported_requirement():
    deps, warnings = parse_requirements(
        "-r common.txt\nrequests==2.28.0",
        "requirements.txt",
    )

    assert len(deps) == 1
    assert len(warnings) == 1


def test_complete_repository_scan(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "flask==2.2.0\n",
        encoding="utf-8",
    )

    frontend = tmp_path / "frontend"
    frontend.mkdir()

    (frontend / "package.json").write_text(
        '{"dependencies":{"react":"18.2.0"}}',
        encoding="utf-8",
    )

    report = extract_dependencies(tmp_path)

    assert report["dependency_count"] == 2

    names = {
        dependency["name"]
        for dependency in report["dependencies"]
    }

    assert names == {"flask", "react"}
    assert report["warnings"] == []

