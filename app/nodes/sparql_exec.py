from pathlib import Path
from app.tools.brick_store import BrickStore

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BRICK_TTL = DATA_DIR / "site_generated.ttl"
BRICK = BrickStore(BRICK_TTL)

def run_sparql(sparql: str):
    return BRICK.query(sparql)
