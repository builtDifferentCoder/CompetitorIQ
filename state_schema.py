"""Root export for state_schema.py referencing backend/app/schemas/state_schema.py."""
import sys
from pathlib import Path

# Add backend directory to sys.path for convenient root imports
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.state_schema import (  # noqa: E402
    CompetitorIQState,
    Finding,
    ResearchDomain,
    ResearchTask,
    SourceItem,
)

__all__ = [
    "CompetitorIQState",
    "Finding",
    "ResearchDomain",
    "ResearchTask",
    "SourceItem",
]
