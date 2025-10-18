from app.graph import agent

def cli():
    print("LangGraph 多 Agent 模式：输入自然语言提问，exit 退出。")
    while True:
        q = input("\nYou: ").strip()
        if q.lower() in ["exit", "quit", "q"]:
            break
        result = agent.invoke({"question": q})
        print("\n[SPARQL]")
        print(result["sparql"])
        print("\n[ANSWER]")
        print(result["answer"])

if __name__ == "__main__":
    cli()
