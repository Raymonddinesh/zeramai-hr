# Re-export everything from schemas_base (the original schemas.py) so that
# existing imports like ``from app.schemas import CandidateCreate`` keep working
# while app.schemas is now a proper package that can also host submodules
# (company_legal_profile, manager, etc.).
from app.schemas_base import *  # noqa: F401,F403
