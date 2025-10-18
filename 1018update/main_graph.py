# main_graph.py
from app.graph import agent

def cli(stream: bool = True):
    print("LangGraph 多 Agent 模式：输入自然语言提问，exit 退出。")
    while True:
        q = input("\nYou: ").strip()
        if q.lower() in ["exit", "quit", "q"]:
            break

        # —— 可视化 LangGraph 的事件流 ——
        if stream:
            print("\n[STREAM]")
            for ev in agent.stream({"question": q}):
                # ev 里通常包含当前节点名/增量状态；为简洁只打印键
                print("  ", list(ev.keys()))

        result = agent.invoke({"question": q})

        # 兼容可能缺字段的情况，避免 KeyError
        sparql = result.get("sparql", "(no sparql)")
        answer = result.get("answer", "(no answer)")

        print("\n[SPARQL]")
        print(sparql)
        print("\n[ANSWER]")
        print(answer)

if __name__ == "__main__":
    cli(stream=True)
