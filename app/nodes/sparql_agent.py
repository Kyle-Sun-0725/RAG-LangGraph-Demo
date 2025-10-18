from app.tools.brick_store import BrickStore
from pathlib import Path
import re

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BRICK_TTL = DATA_DIR / "site_generated.ttl"
BRICK = BrickStore(BRICK_TTL)

def execute_query(sparql: str):
    rows = BRICK.query(sparql)

    # 统一任何 tsid 变体为 'tsid'（ts_id / max_tsid / min_tsid / TSID 等）
    for r in rows:
        keys = list(r.keys())
        tsid_keys = [k for k in keys if re.search(r"ts[_-]?id", k, re.I)]
        # 取第一个有值的
        picked = next((k for k in tsid_keys if r.get(k)), (tsid_keys[0] if tsid_keys else None))
        if picked:
            r["tsid"] = r[picked]
            for k in tsid_keys:
                if k != picked and k in r:
                    del r[k]
    return rows
