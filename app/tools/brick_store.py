from rdflib import Graph
from pathlib import Path

class BrickStore:
    def __init__(self, ttl_path: Path):
        self.g = Graph()
        p = ttl_path.resolve()
        self.g.parse(p.as_uri(), format="turtle")

    def query(self, sparql: str):
        q = self.g.query(sparql)
        cols = [str(v) for v in q.vars]
        return [{cols[i]: str(r[i]) for i in range(len(cols))} for r in q]
