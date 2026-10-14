"""
Comparison script facade with correct spelling.
"""
from .comapre import compare_versions

__all__ = ["compare_versions"]

if __name__ == "__main__":
    from .cli import main
    import sys
    sys.exit(main())
