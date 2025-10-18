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
    error: str  # 错误兜底

# 1) RAG Agent 节点，新增了兜底进入error
def node_rag(state: PipelineState):
    try:
        question = state.get("question", "")
        if not question:
            return {"error": "缺少 question"}
        sparql = generate_sparql(question)
        return {"sparql": sparql}
    except Exception as e:
        return {"error": f"RAG失败: {e}"}

# 2) SPARQL Agent 节点，新增了兜底进入error
def node_sparql(state: PipelineState):
    try:
        sparql = state.get("sparql", "")
        if not sparql:
            return {"query_result": []}  # 没生成就跳过
        res = execute_query(sparql)
        return {"query_result": res or []}
    except Exception as e:
        return {"error": f"SPARQL失败: {e}"}

# 3) Analysis Agent 节点（如果有 tsid）
def node_analysis(state: dict):
    try:
        q = (state.get("question") or "")
        res = state.get("query_result") or []
        # —— 以下保持你原来的逻辑（关键词判断 + tsid 抽取 + analyze_timeseries）——
        kw = ["平均","均值","最高","最低","趋势","变化","昨天","昨儿","昨儿个",
              "average","mean","max","maximum","min","minimum","trend","change","yesterday"]
        if not res or not any(k in q.lower() for k in kw):
            return {"analysis_result": []}
        tsid = res[0].get("tsid")
        if not tsid:
            for k, v in res[0].items():
                if "tsid" in k.lower():
                    tsid = v; break
        if not tsid:
            return {"analysis_result": []}
        ql = q.lower()
        need_avg = any(k in ql for k in ["平均","均值","avg","average","mean"])
        need_max = any(k in ql for k in ["最高","max","maximum"])
        need_min = any(k in ql for k in ["最低","min","minimum"])
        need_trend = any(k in ql for k in ["趋势","trend","变化","change"])
        if not (need_avg or need_max or need_min or need_trend):
            need_avg = True
        analysis = analyze_timeseries(
            tsid=tsid, question=q,
            need_avg=need_avg, need_max=need_max, need_min=need_min, need_trend=need_trend,
        )
        return {"analysis_result": [analysis]}
    except Exception as e:
        return {"error": f"分析失败: {e}"}

# 4) Answer Agent 节点
def node_answer(state: PipelineState):
    # 1) 先处理错误兜底
    if state.get("error"):
        return {"answer": f"处理失败：{state['error']}"}

    # 2) 安全读取，防止 KeyError
    analysis = state.get("analysis_result") or []
    query_res = state.get("query_result") or []
    question = state.get("question", "")

    # 3) 有分析结果就用分析结果；否则用 SPARQL 查询结果（可能为空）
    if analysis:
        text = to_natural_language(question, analysis)
    else:
        text = to_natural_language(question, query_res)

    return {"answer": text}

def has_error(state: PipelineState):
    return "end" if state.get("error") else "go"

def need_sparql(state: PipelineState):
    return "run" if state.get("sparql") else "skip"

def need_analysis(state: PipelineState):
    res = state.get("query_result") or []
    q = (state.get("question") or "").lower()
    kw = ["平均","均值","最高","最低","趋势","变化",
          "average","mean","max","maximum","min","minimum","trend","change"]
    has_kw = any(k in q for k in kw)
    has_tsid = bool(res and ("tsid" in res[0]))
    return "run" if (has_kw and has_tsid) else "skip"

# 构建图
workflow = StateGraph(PipelineState)
workflow.add_node("rag", node_rag)
workflow.add_node("sparql", node_sparql)
workflow.add_node("analysis", node_analysis)
workflow.add_node("answer", node_answer)

# 入口
workflow.add_edge(START, "rag")

# rag 之后：若报错 -> END；否则 有/无 sparql 决定去向
def route_after_rag(state: PipelineState):
    if state.get("error"):
        return "end"
    return "run" if state.get("sparql") else "skip"

workflow.add_conditional_edges(
    "rag",
    route_after_rag,
    {
        "end": END,        # 出错 -> 结束
        "run": "sparql",   # 有 sparql -> 执行 SPARQL
        "skip": "answer",  # 无 sparql -> 直接回答
    },
)

# sparql 之后：若报错 -> END；否则 只有问统计/趋势且有 tsid 才进 analysis
def route_after_sparql(state: PipelineState):
    if state.get("error"):
        return "end"
    res = state.get("query_result") or []
    q = (state.get("question") or "").lower()
    kw = ["平均","均值","最高","最低","趋势","变化",
          "average","mean","max","maximum","min","minimum","trend","change"]
    has_kw = any(k in q for k in kw)
    has_tsid = bool(res and ("tsid" in res[0]))
    return "run" if (has_kw and has_tsid) else "skip"

workflow.add_conditional_edges(
    "sparql",
    route_after_sparql,
    {
        "end": END,          # 出错 -> 结束
        "run": "analysis",   # 意图+tsid 具备 -> 去分析
        "skip": "answer",    # 否则 -> 直接回答
    },
)

# analysis 之后：若报错 -> END；否则 -> answer
def route_after_analysis(state: PipelineState):
    return "end" if state.get("error") else "answer"

workflow.add_conditional_edges(
    "analysis",
    route_after_analysis,
    {
        "end": END,
        "answer": "answer",
    },
)

# answer -> END
workflow.add_edge("answer", END)

agent = workflow.compile()