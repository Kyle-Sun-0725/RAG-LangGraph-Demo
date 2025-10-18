from app.nodes.rag_agent import generate_sparql
from app.nodes.sparql_exec import run_sparql

'''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~测试一下，顺手算一下平均温度~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''
import pandas as pd
from datetime import datetime, timedelta
from dateutil import tz
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / "data" / "telemetry_generated.csv"

def avg_yesterday(tsid: str, tz_name="China/Beijing"):
    df = pd.read_csv(CSV, parse_dates=["timestamp"])
    tzinfo = tz.gettz(tz_name)
    now = datetime.now(tzinfo)
    start = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1))
    end = start + timedelta(days=1)
    m = (df["measure_id"].eq(tsid)
         & (df["timestamp"] >= pd.Timestamp(start.replace(tzinfo=None)))
         & (df["timestamp"] <  pd.Timestamp(end.replace(tzinfo=None))))
    d = df.loc[m, "value"].astype(float)
    return (start.date(), float(d.mean())) if not d.empty else (start.date(), None)
'''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~测试一下，顺手算一下平均温度~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

def cli():
    print("RAG 模式：请输入自然语言问题（例如：'Room 3 有哪些传感器？' 或 'Room 3 的温度传感器 ts_id 是什么'）")
    print("输入 exit 退出。")
    # print(f"cwd = {os.getcwd()}")
    while True:
        q = input("\nYou: ").strip()
        if q.lower() in ["exit", "quit", "q"]:
            break

        sparql = generate_sparql(q)
        print("\n[SPARQL]")
        print(sparql)

        try:
            rows = run_sparql(sparql)
            print("\n[RESULT]")
            if not rows:
                print("(空结果)")
            else:
                for r in rows:
                    print(r)

                # 在打印RESULT之后，开发者手动验证用——当查询返回里含 'tsid' 字段时：
                if rows and "tsid" in rows[0]:
                    day, avg = avg_yesterday(rows[0]["tsid"])
                    print(f"\n[CHECK] {day} 的平均温度：{avg if avg is not None else '无数据'} °C")

        except Exception as e:
            print("\n[ERROR]")
            print(repr(e))

if __name__ == "__main__":
    cli()
