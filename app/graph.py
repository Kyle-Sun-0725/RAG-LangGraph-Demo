from langgraph.graph import StateGraph, START, END
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
import operator
from app.nodes.rag_agent import generate_sparql
from app.nodes.sparql_agent import execute_query
from app.nodes.analysis_agent import analyze_timeseries
from app.nodes.answer_agent import to_natural_language

# 定义共享状态
class PipelineState(TypedDict):
    question: str
    sparql: str
    query_result: list
    analysis_result: list
    answer: str

# 1) RAG Agent 节点
def node_rag(state: PipelineState):
    sparql = generate_sparql(state["question"])
    return {"sparql": sparql}

# 2) SPARQL Agent 节点
def node_sparql(state: PipelineState):
    res = execute_query(state["sparql"])
    return {"query_result": res}

# 3) Analysis Agent 节点（如果有 tsid）
def node_analysis(state: dict):
    q = (state["question"] or "")
    res = state["query_result"]

    # 中英混合关键词（平均/极值/趋势/时间）
    kw = [
        "平均","均值","最高","最低","趋势","变化","昨天","昨儿","昨儿个",
        "average","mean","max","maximum","min","minimum","trend","change","yesterday"
    ]
    if not res or not any(k in q.lower() for k in kw):
        return {"analysis_result": []}

    # 取 tsid（已在 sparql_agent 归一化）；没有则尝试在首条里找包含 tsid 的键
    tsid = res[0].get("tsid")
    if not tsid:
        for k, v in res[0].items():
            if "tsid" in k.lower():
                tsid = v; break
    if not tsid:
        return {"analysis_result": []}

    # 从问句识别想要的统计（中英）
    ql = q.lower()
    need_avg = any(k in ql for k in ["平均","均值","avg","average","mean"])
    need_max = any(k in ql for k in ["最高","max","maximum"])
    need_min = any(k in ql for k in ["最低","min","minimum"])
    need_trend = any(k in ql for k in ["趋势","trend","变化","change"])

    # 没明确提就默认给平均
    if not (need_avg or need_max or need_min or need_trend):
        need_avg = True

    analysis = analyze_timeseries(
        tsid=tsid,
        question=q,
        need_avg=need_avg,
        need_max=need_max,
        need_min=need_min,
        need_trend=need_trend,
    )
    return {"analysis_result": [analysis]}

# 4) Answer Agent 节点
def node_answer(state: PipelineState):
    if state["analysis_result"]:
        text = to_natural_language(state["question"], state["analysis_result"])
    else:
        text = to_natural_language(state["question"], state["query_result"])
    return {"answer": text}

# 构建图
workflow = StateGraph(PipelineState)
workflow.add_node("rag", node_rag)
workflow.add_node("sparql", node_sparql)
workflow.add_node("analysis", node_analysis)
workflow.add_node("answer", node_answer)

workflow.add_edge(START, "rag")
workflow.add_edge("rag", "sparql")
workflow.add_edge("sparql", "analysis")
workflow.add_edge("analysis", "answer")
workflow.add_edge("answer", END)

agent = workflow.compile()
