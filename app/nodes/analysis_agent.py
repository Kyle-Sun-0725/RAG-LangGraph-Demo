import pandas as pd, numpy as np
from datetime import datetime, timedelta
from dateutil import tz
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "data" / "telemetry_generated.csv"

def resolve_timespan(natural: str, tz_name="China/Beijing"):
    q = (natural or "").lower()
    tzinfo = tz.gettz(tz_name)
    now = datetime.now(tzinfo)
    if any(k in q for k in ["昨儿","昨儿个","昨天","yesterday"]):
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        end = start + timedelta(days=1)
        return start, end, f"{start.date()}"
    # 默认昨天
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    end = start + timedelta(days=1)
    return start, end, f"{start.date()}"

# 量纲映射（中英都可触发）
_METRIC_MAP = [
    (["温度","temperature","temp"],         ("temperature","温度","°C")),
    (["湿度","humidity"],                   ("humidity","湿度","%RH")),
    (["光照","照度","illuminance","lux"],   ("illuminance","光照强度","lux")),
    (["噪声","噪音","noise","sound"],       ("noise","噪声","dB")),
    (["开关","switch","on/off"],            ("switch","开关状态","%")),
]
# 若问句不包含量纲词，兜底
_DEFAULT_METRIC = ("value","数值","")

def detect_metric_and_unit(question: str):
    q = (question or "").lower()
    for keys, info in _METRIC_MAP:
        if any(k in q for k in keys):
            return info  # (metric_key, metric_zh, unit)
    return _DEFAULT_METRIC

def _trend_label(values: pd.Series):
    if values.size < 3: return None
    x = np.arange(values.size)
    slope = np.polyfit(x, values.values, 1)[0]
    if slope > 0.02:  return "上升"
    if slope < -0.02: return "下降"
    return "基本稳定"

def analyze_timeseries(tsid: str, question: str,
                       need_avg=True, need_max=False, need_min=False, need_trend=False,
                       tz_name="China/Beijing"):
    start, end, span = resolve_timespan(question, tz_name)
    metric_key, metric_zh, unit = detect_metric_and_unit(question)

    df = pd.read_csv(CSV, parse_dates=["timestamp"])
    m = (df["measure_id"].eq(tsid)
         & (df["timestamp"] >= pd.Timestamp(start.replace(tzinfo=None)))
         & (df["timestamp"] <  pd.Timestamp(end.replace(tzinfo=None))))
    vals = df.loc[m, "value"].astype(float)

    res = {"span": span, "metric": metric_key, "metric_zh": metric_zh, "unit": unit, "n": int(vals.size)}
    if vals.empty:
        res.update({"avg": None, "max": None, "min": None, "trend": None})
        return res

    res["avg"]   = float(vals.mean()) if need_avg   else None
    res["max"]   = float(vals.max())  if need_max   else None
    res["min"]   = float(vals.min())  if need_min   else None
    res["trend"] = _trend_label(vals) if need_trend else None
    return res
