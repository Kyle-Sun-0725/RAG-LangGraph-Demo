# 自己搓一点供测试的数据出来
import os
import random
from datetime import datetime, timedelta, time
from dateutil import tz
import pandas as pd

BUILDING_NS = "http://example.com/building#"
NUM_ROOMS = 500
POINTS_PER_DAY = 24
USER_TZ = "China/Beijing"

TEMP_RANGE = (21.0, 25.0)
HUMI_RANGE = (35.0, 55.0)
LUX_DAY_RANGE = (200.0, 600.0)
LUX_NIGHT_RANGE = (5.0, 30.0)
NOISE_RANGE = (35.0, 65.0)

OCCUPIED_START = time(8, 0)
OCCUPIED_END = time(18, 0)
SWITCH_ON_PROB_OCCUPIED = 0.9
SWITCH_ON_PROB_IDLE = 0.1

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
TTL_PATH = os.path.join(DATA_DIR, "site_generated.ttl")
CSV_PATH = os.path.join(DATA_DIR, "telemetry_generated.csv")

# Turtle 头部（Brick 常用前缀）
TTL_HEADER = f"""@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix bldg:  <{BUILDING_NS}> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .

"""

# 每个房间要生成的点（名称前缀 -> Brick 类型）
POINTS_SPEC = {
    "Temp_Sensor":  "brick:Temperature_Sensor",
    "Humi_Sensor":  "brick:Humidity_Sensor",
    "Lux_Sensor":   "brick:Illuminance_Sensor",
    "Noise_Sensor": "brick:Noise_Sensor",
    # 两个开关用命令点（On_Off_Command）
    "Light_Switch": "brick:On_Off_Command",
    "HVAC_Switch":  "brick:On_Off_Command",
}

# ts_id 命名
# 例如：room3_temp、room3_humi、room3_lux、room3_noise、room3_light_switch、room3_hvac_switch
def build_tsid(room_no: int, kind: str) -> str:
    kind_map = {
        "Temp_Sensor":  "temp",
        "Humi_Sensor":  "humi",
        "Lux_Sensor":   "lux",
        "Noise_Sensor": "noise",
        "Light_Switch": "light_switch",
        "HVAC_Switch":  "hvac_switch",
    }
    return f"room{room_no}_{kind_map[kind]}"

def gen_room_ttl(room_no: int) -> str:
    """
    生成一个房间及其所有点位的 Turtle 片段：
    - bldg:Room_{n} a brick:Room ; rdfs:label "Room n" ; brick:hasPoint ... .
    - 每个点位：类型 + label + bldg:ts_id "..."
    """
    room_uri = f"bldg:Room_{room_no}"

    # 列出所有点的 URI，放到同一个 hasPoint 语句里（逗号分隔）
    point_uris = [f"bldg:{prefix}_{room_no}" for prefix in POINTS_SPEC.keys()]
    haspoint_line = "    brick:hasPoint " + " , ".join(point_uris) + " .\n"

    ttl = []
    ttl.append(f"{room_uri} a brick:Room ;")
    ttl.append(f'    rdfs:label "Room {room_no}" ;')
    ttl.append(haspoint_line)

    # 逐个点写出类型/label/ts_id
    for prefix, brick_type in POINTS_SPEC.items():
        uri = f"bldg:{prefix}_{room_no}"
        label = f"Room {room_no} {prefix.replace('_', ' ')}"
        tsid = build_tsid(room_no, prefix)
        ttl.append(f"{uri} a {brick_type} ;")
        ttl.append(f'    rdfs:label "{label}" ;')
        ttl.append(f'    bldg:ts_id "{tsid}" .\n')

    return "\n".join(ttl)

def get_yesterday_local_range():
    """
    返回昨天的 [start, end)（timezone-aware datetime）
    """
    local_tz = tz.gettz(USER_TZ)
    now_local = datetime.now(local_tz)
    start = (now_local.replace(hour=0, minute=0, second=0, microsecond=0)
             - timedelta(days=1))
    end = start + timedelta(days=1)
    return start, end

def gen_time_points(start_local: datetime, end_local: datetime, points_per_day: int):
    """
    均匀生成昨天的时间点列表（timezone-aware），
    输出时写入CSV为naive字符串。
    """
    if points_per_day <= 0:
        raise ValueError("POINTS_PER_DAY must be > 0")
    delta = (end_local - start_local) / points_per_day
    times = [start_local + i * delta for i in range(points_per_day)]
    # 写 CSV 用 naive（无时区）ISO 字符串，保持和你的现有筛选逻辑一致
    return [t.replace(tzinfo=None) for t in times]

def is_occupied(dt_local_naive: datetime) -> bool:
    """
    简单判断“上班时间”
    """
    tt = dt_local_naive.time()
    return OCCUPIED_START <= tt < OCCUPIED_END

def sample_switch_value(dt_local_naive: datetime) -> int:
    """
    按上班/非上班概率生成 0/1
    """
    if is_occupied(dt_local_naive):
        return 1 if random.random() < SWITCH_ON_PROB_OCCUPIED else 0
    else:
        return 1 if random.random() < SWITCH_ON_PROB_IDLE else 0

def sample_lux_value(dt_local_naive: datetime) -> float:
    if is_occupied(dt_local_naive):
        v = random.uniform(*LUX_DAY_RANGE)
    else:
        v = random.uniform(*LUX_NIGHT_RANGE)
    return round(v, 2)

def sample_temp_value() -> float:
    return round(random.uniform(*TEMP_RANGE), 2)

def sample_humi_value() -> float:
    return round(random.uniform(*HUMI_RANGE), 2)

def sample_noise_value() -> float:
    return round(random.uniform(*NOISE_RANGE), 2)

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def generate_ttl():
    print(f"[1/3] 生成 Brick TTL → {TTL_PATH}")
    chunks = [TTL_HEADER]
    for i in range(1, NUM_ROOMS + 1):
        chunks.append(gen_room_ttl(i))
    with open(TTL_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(chunks))
    print("    ✓ site_generated.ttl 已生成")

def generate_csv():
    print(f"[2/3] 计算“昨天”的时间范围（{USER_TZ}）")
    start_y, end_y = get_yesterday_local_range()
    times = gen_time_points(start_y, end_y, POINTS_PER_DAY)
    print(f"    ✓ {start_y.date()} 共 {len(times)} 个时间点/每点位")

    print(f"[3/3] 生成时序数据 CSV → {CSV_PATH}")
    rows = []
    for room_no in range(1, NUM_ROOMS + 1):
        # ts_id
        ts_temp  = build_tsid(room_no, "Temp_Sensor")
        ts_humi  = build_tsid(room_no, "Humi_Sensor")
        ts_lux   = build_tsid(room_no, "Lux_Sensor")
        ts_noise = build_tsid(room_no, "Noise_Sensor")
        ts_light = build_tsid(room_no, "Light_Switch")
        ts_hvac  = build_tsid(room_no, "HVAC_Switch")

        for t in times:
            # 传感器
            rows.append({"timestamp": t.isoformat(), "measure_id": ts_temp,  "value": sample_temp_value()})
            rows.append({"timestamp": t.isoformat(), "measure_id": ts_humi,  "value": sample_humi_value()})
            rows.append({"timestamp": t.isoformat(), "measure_id": ts_lux,   "value": sample_lux_value(t)})
            rows.append({"timestamp": t.isoformat(), "measure_id": ts_noise, "value": sample_noise_value()})
            # 开关（0/1）
            rows.append({"timestamp": t.isoformat(), "measure_id": ts_light, "value": sample_switch_value(t)})
            rows.append({"timestamp": t.isoformat(), "measure_id": ts_hvac,  "value": sample_switch_value(t)})

    df = pd.DataFrame(rows, columns=["timestamp", "measure_id", "value"])
    df.to_csv(CSV_PATH, index=False)
    print("    ✓ telemetry_generated.csv 已生成")

def main():
    ensure_dirs()
    generate_ttl()
    generate_csv()
    print("\n完成！现在你可以在程序里直接使用：")
    print(f"  - Brick 模型：{TTL_PATH}")
    print(f"  - 时序数据：{CSV_PATH}")
    print("点位 ts_id 命名示例：room3_temp / room3_humi / room3_lux / room3_noise / room3_light_switch / room3_hvac_switch")

if __name__ == "__main__":
    main()
