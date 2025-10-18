from collections import Counter

def _fmt(v, unit):
    return f"{v:.2f}{(' ' + unit) if unit else ''}"

def to_natural_language(question: str, result: list[dict]) -> str:
    if not result: return "没查到相关结果。"
    first = result[0]

    # 分析结果（avg/max/min/trend）
    if "span" in first and "metric_zh" in first:
        span = first["span"]; unit = first.get("unit",""); name = first.get("metric_zh","数值"); n = first.get("n")
        parts = []
        if first.get("max") is not None: parts.append(f"最高{name} {_fmt(first['max'], unit)}")
        if first.get("min") is not None: parts.append(f"最低{name} {_fmt(first['min'], unit)}")
        if first.get("avg") is not None and not parts:  # 若只问平均或没提极值
            parts.append(f"平均{name} {_fmt(first['avg'], unit)}")
        if first.get("trend"): parts.append(f"趋势：{first['trend']}")
        tail = f"（样本 {n} 条）" if n is not None else ""
        # 若同时问“最高、最低”，两者都会被拼进 parts；只问“最低”则只会有最低
        return f"{span}：{('，'.join(parts))}{tail}。"

    # 传感器清单（带类型统计）
    if "sensor" in first and "type" in first:
        sensors = [r["sensor"].split("#")[-1] for r in result]
        types = [r["type"].split("#")[-1] for r in result]
        counts = Counter(types)
        stats = "，".join([f"{t}×{c}" for t, c in counts.items()])
        return f"{question} —— 共 {len(sensors)} 个（{stats}）：{('、'.join(sensors))}。"

    # 仅 tsid
    if set(first.keys()) == {"tsid"} or ("tsid" in first and len(first)==1):
        return f"传感器的 ts_id 是 {first['tsid']}。"

    # 兜底：把每条记录格式化
    rows = []
    for r in result:
        rows.append("，".join([f"{k}={v.split('#')[-1] if isinstance(v,str) else v}" for k, v in r.items()]))
    return "；".join(rows)
