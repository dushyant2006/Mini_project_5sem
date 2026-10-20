"""
Comparison script facade with correct spelling.
"""
try:
    from .comapre import compare_versions
except ImportError:
    from codedrift.comapre import compare_versions

__all__ = ["compare_versions"]

if __name__ == "__main__":
    from .cli import main
    import sys
    sys.exit(main())
