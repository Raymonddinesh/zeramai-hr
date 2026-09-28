import pathlib, sys
# Ensure repository root is in sys.path for pytest collection
_repo_root = pathlib.Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
