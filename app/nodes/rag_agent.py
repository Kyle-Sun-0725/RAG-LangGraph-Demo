# app/nodes/rag_agent.py
import os
from pathlib import Path
from rdflib import Graph, RDF, RDFS, Namespace
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model

BRICK = Namespace("https://brickschema.org/schema/Brick#")
BLDG  = Namespace("http://example.com/building#")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT.parent / "data"
TTL = DATA_DIR / "site_generated.ttl"
INDEX_DIR = DATA_DIR / "faiss_index"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "sparql_brick.md"

# --- 1) 构建/加载向量索引（把 TTL 变成可检索文本） ---
def _ttl_to_text_docs(ttl: Path):
    g = Graph()
    p = ttl.resolve()  # Path
    g.parse(p.as_uri(), format="turtle")
    docs = []

    # 房间：基础描述
    for room in g.subjects(RDF.type, BRICK.Room):
        label = next(g.objects(room, RDFS.label), "")
        docs.append(f"{room.split('#')[-1]} rdf:type Room; label={label}")

        # 房间的点位及类型/ts_id
        for sensor in g.objects(room, BRICK.hasPoint):
            types = [str(t).split("#")[-1] for t in g.objects(sensor, RDF.type)]
            tsid  = next((str(x) for x in g.objects(sensor, BLDG.ts_id)), "")
            sname = sensor.split('#')[-1]
            docs.append(f"{room.split('#')[-1]} hasPoint {sname} (types={','.join(types)}; ts_id={tsid})")

    # 传感器/命令点：类型提示
    for s in g.subjects(RDF.type, None):
        for t in g.objects(s, RDF.type):
            tname = str(t).split("#")[-1]
            if "Sensor" in tname or "Command" in tname:
                docs.append(f"{s.split('#')[-1]} rdf:type {tname}")

    return docs

def load_or_build_index():
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if INDEX_DIR.exists():
        return FAISS.load_local(str(INDEX_DIR), emb, allow_dangerous_deserialization=True), emb
    docs = _ttl_to_text_docs(TTL)
    vs = FAISS.from_texts(docs, embedding=emb)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vs.save_local(str(INDEX_DIR))
    return vs, emb

VS, EMB = load_or_build_index()

# --- 2) DeepSeek 模型---
LLM = init_chat_model(
    "deepseek:deepseek-chat",
    temperature=0,
    api_key=os.environ.get("DEEPSEEK_API_KEY")  # 环境变量
)

def retrieve_context(question: str, k: int = 8) -> str:
    docs = VS.similarity_search(question, k=k)
    return "\n".join(d.page_content for d in docs)

def generate_sparql(question: str) -> str:
    context = retrieve_context(question)
    tmpl = Path(PROMPT_PATH).read_text(encoding="utf-8")
    prompt = tmpl.format(question=question, context=context)
    resp = LLM.invoke(prompt)
    # 去掉可能的反引号包装
    return resp.content.strip().strip("`").strip()
