# Update Log – From LangChain to LangGraph

## 概述

本次更新的核心目标是：  
> 将项目从 **LangChain 式线性流程**，升级为真正的 **LangGraph 状态驱动图结构**，  
> 在保持原有功能（RAG → SPARQL → Analysis → Answer）不变的前提下，实现：
>
> - **节点化执行** 
> - **条件路由**
> - **错误短路**
> - **事件流可视化**

修改了main_graph.py以及graph.py，存于1018update目录下
---

## 旧架构：更像LangChain风格的逻辑链

旧版代码（`graph.py` + `main_graph.py`）中：
- 节点按固定顺序执行：
  ```
  START → rag → sparql → analysis → answer → END
  ```
- 每个节点强依赖上游结果，无条件判断。
- 任一阶段失败会直接抛异常（KeyError / NoneType）。
- CLI 仅执行 `agent.invoke()`，无法观察中间过程。

> e.g. 旧版本代码直接提问“Room 10086 昨天的最低噪声是多少?”，不会抛出错误，但是这是由于answer_agent中做了异常处理，为结构的不足做了兜底。

---

## 新架构：引入了条件边形成的LangGraph图状结构

### LangGraph 的关键特征
| 特征 | 说明 |
|------|------|
| **节点（这个此前的版本已经设置好）** | 每个 Agent 是一个节点 (`workflow.add_node("rag", node_rag)`) |
| **条件边** | 通过 `add_conditional_edges()` 控制流程走向 |
| **路由函数** | 依据 `state` 返回分支名，如 `route_after_rag()` |
| **错误短路机制** | 节点异常写入 `state["error"]`，立即跳转 END |
| **（展示用）事件流可视化** | 使用 `agent.stream()` 打印实际执行路径（参见1018update/main_graph.py） |

---

### 节点与条件边

```python
# 条件路由示例，参见1018update/graph.py
workflow.add_conditional_edges(
    "rag",
    route_after_rag,
    {
        "end": END,        # 出错 -> 结束
        "run": "sparql",   # 有 sparql -> 执行 SPARQL
        "skip": "answer",  # 无 sparql -> 直接回答
    },
)
```

这意味着：
- 如果 RAG 成功生成 SPARQL → 转入 SPARQL 节点；  
- 如果失败 → 跳到 Answer ；（因为Answer顶部有容错，可以丢进去）
- 如果出错 → 跳到 END。  （保留这个位子，在容错机制不足的情况下兜底）

LangChain 无法直接表达这种“根据运行状态切换路径”的结构。

---

### 三个关键改动
| 改动点 | 描述 | 文件 |
|--------|------|------|
| 条件边路由 | 使用 `route_after_rag` / `route_after_sparql` / `route_after_analysis` 实现动态分支 | `graph.py` |
| 错误兜底 | 通过`try/except`，将错误写入 `state["error"]`，跳转至 END | `graph.py` |
| 节点状态输出 | `agent.stream()` 实时打印节点流转顺序 | `main_graph.py` |


## 示例运行
可以注意到，当数据不存在时跳过了 `analysis` 节点。

```text
You: Room 2 昨天的最低噪声是多少?

[STREAM]
   ['rag']
   ['sparql']
   ['analysis']
   ['answer']

[SPARQL]
SELECT ?tsid WHERE {
  bldg:Room_2 rdf:type brick:Room .
  bldg:Room_2 brick:hasPoint ?sensor .
  ?sensor rdf:type brick:Noise_Sensor .
  ?sensor bldg:ts_id ?tsid .
} LIMIT 1

[ANSWER]
2025-10-17：最低噪声 37.22 dB（样本 24 条）。
```

```text
You: Room 10086 昨天的最低噪声是多少?

[STREAM]
   ['rag']
   ['sparql']
   ['answer']

[SPARQL]
SELECT ?tsid WHERE {
  bldg:Room_10086 rdf:type brick:Room .
  bldg:Room_10086 brick:hasPoint ?sensor .
  ?sensor rdf:type brick:Noise_Sensor .
  ?sensor bldg:ts_id ?tsid .
} LIMIT 1

[ANSWER]
没查到相关结果。
```

---
