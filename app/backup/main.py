from rdflib import Graph
import pandas as pd
from dateutil import tz
from datetime import datetime, timedelta
from pathlib import Path
import os

# --- 用 __file__ 推导项目根目录（main.py 在 app/ 下，因此 parent.parent 是项目根）---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

BRICK_TTL = DATA_DIR / "site_generated.ttl"
CSV_PATH  = DATA_DIR / "telemetry_generated.csv"

# 1) 加载 Brick 图谱（先检查文件是否存在，给出清晰报错）
if not BRICK_TTL.exists():
    raise FileNotFoundError(f"找不到 Brick TTL 文件：{BRICK_TTL}")
if not CSV_PATH.exists():
    print(f"⚠️  警告：CSV 文件目前找不到：{CSV_PATH}")

g = Graph()
g.parse(str(BRICK_TTL), format="turtle")

# 把房间号转成 URI
def room_uri(room_no: str) -> str:
    return f"http://example.com/building#Room_{room_no}"

# A. 查询“这个房间有哪些传感器？”
def list_sensors_in_room(room_no: str):
    sparql = f"""
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?sensor ?type WHERE {{
      <{room_uri(room_no)}> rdf:type brick:Room .
      <{room_uri(room_no)}> brick:hasPoint ?sensor .
      ?sensor rdf:type ?type .
    }}
    """
    qres = g.query(sparql)
    rows = []
    for row in qres:
        rows.append({
            "sensor": str(row.sensor),
            "type": str(row.type).split("#")[-1]
        })
    return rows

# B. 通过 Brick 查到房间温度传感器的 ts_id，再去 CSV 里算“昨天平均”
def avg_temp_yesterday(room_no: str, user_tz: str = "China/Beijing"):
    # 先查传感器和 ts_id
    sparql = f"""
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX bldg:  <http://example.com/building#>
    PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?tsid WHERE {{
      <{room_uri(room_no)}> rdf:type brick:Room .
      <{room_uri(room_no)}> brick:hasPoint ?sensor .
      ?sensor rdf:type brick:Temperature_Sensor .
      ?sensor bldg:ts_id ?tsid .
    }}
    LIMIT 1
    """
    qres = g.query(sparql)
    tsid = None
    for row in qres:
        tsid = str(row.tsid)
    if not tsid:
        return None, "在 Brick 里没找到这个房间的温度传感器或 ts_id"

    # 读 CSV，筛“昨天”的数据
    if not CSV_PATH.exists():
        return None, f"找不到 CSV：{CSV_PATH}"
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])

    # 把用户时区考虑进去（用于确定“昨天”的日界）
    tzinfo = tz.gettz(user_tz)
    now_local = datetime.now(tzinfo)
    start_yesterday = (now_local.replace(hour=0, minute=0, second=0, microsecond=0)
                       - timedelta(days=1))
    end_yesterday = start_yesterday + timedelta(days=1)

    # 假设 CSV 的时间是“本地无时区字符串”，与之前生成脚本一致
    mask = (
        (df["measure_id"] == tsid) &
        (df["timestamp"] >= pd.Timestamp(start_yesterday.replace(tzinfo=None))) &
        (df["timestamp"] <  pd.Timestamp(end_yesterday.replace(tzinfo=None)))
    )
    d = df.loc[mask]
    if d.empty:
        return None, f"没有 {start_yesterday.date()} 的数据（ts_id={tsid})"
    avg = d["value"].astype(float).mean()
    return avg, f"{start_yesterday.date()}"

def cli():
    # print("已加载 Brick 与 CSV 路径：")
    # print(f"- BRICK_TTL = {BRICK_TTL}")
    # print(f"- CSV_PATH  = {CSV_PATH}")
    # print(f"- 当前工作目录 cwd = {os.getcwd()}")
    print("\n你可以问：")
    print("1) Room X 有哪些传感器？")
    print("2) Room X 昨天的平均温度是多少？")
    print("输入 exit 退出。")
    while True:
        q = input("\nYou：").strip()
        if q.lower() in ["exit", "quit", "q"]:
            break

        if "有哪些传感器" in q and "Room" in q:
            room_no = "".join([ch for ch in q if ch.isdigit()])
            rows = list_sensors_in_room(room_no)
            if not rows:
                print("Agent：没有查到传感器。")
            else:
                print("Agent：该房间的传感器：")
                for r in rows:
                    print(f"- {r['type']} ({r['sensor']})")

        elif "平均温度" in q and "昨天" in q and "Room" in q:
            room_no = "".join([ch for ch in q if ch.isdigit()])
            avg, info = avg_temp_yesterday(room_no)
            if avg is None:
                print(f"Agent：{info}")
            else:
                print(f"Agent：{info} 的平均温度约为 {avg:.2f} °C")

        else:
            print("Agent：这个最小版本只支持两类问题：")
            print(" - “Room 3574 有哪些传感器？”")
            print(" - “Room 3574 昨天的平均温度是多少？”")

if __name__ == "__main__":
    cli()
