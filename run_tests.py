"""
Zero-Dependency Test Runner for CodeDrift.
Runs all tests using pytest if installed, or built-in test runner as fallback.
Usage:
    python run_tests.py
"""
import inspect
import os
import sys
import time
from importlib import import_module
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).parent / "src"
TESTS_DIR = Path(__file__).parent / "tests"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


def run_all_tests() -> int:
    # Try pytest first if installed
    try:
        import pytest
        print("Using pytest test runner...")
        return pytest.main(["-v", str(TESTS_DIR)])
    except ImportError:
        print("pytest not found. Running built-in test discovery...")

    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    passed = 0
    failed = 0
    errors = []

    start_time = time.time()
    print("=" * 70)
    print("CodeDrift Automated Test Suite")
    print("=" * 70)

    for tf in test_files:
        mod_name = tf.stem
        try:
            mod = import_module(mod_name)
        except Exception as e:
            print(f"[FAIL] {mod_name}: Import Error ({e})")
            failed += 1
            errors.append((mod_name, "import", str(e)))
            continue

        for attr_name in dir(mod):
            if attr_name.startswith("test_") and callable(getattr(mod, attr_name)):
                fn = getattr(mod, attr_name)
                try:
                    # Check if takes args
                    sig = inspect.signature(fn)
                    if len(sig.parameters) == 0:
                        fn()
                    else:
                        fn(None)
                    print(f"  [PASS] {mod_name}::{attr_name}")
                    passed += 1
                except Exception as exc:
                    print(f"  [FAIL] {mod_name}::{attr_name}: {exc}")
                    failed += 1
                    errors.append((mod_name, attr_name, str(exc)))

    duration = time.time() - start_time
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed in {duration:.2f}s")
    if failed == 0:
        print("[SUCCESS] All test cases passed with 100% success rate.")
        return 0
    else:
        print(f"[ERROR] {failed} test failure(s) detected.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
