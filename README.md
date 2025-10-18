# RAG-LangGraph Demo：基于 Brick Schema 的自然语言查询与数据分析系统

## 一、概述
实现了一个**纯后端多智能体系统（multi-agent system）**，支持使用自然语言查询建筑信息与传感数据。
系统以 **Brick Schema** 为语义基础，结合 **RAG（Retrieval-Augmented Generation）** 与 **LangGraph** 协同实现问答、查询与分析全流程。

---

## 二、学习与构建任务对照

| 邮件任务 | 当前完成情况                                                              |
|-----------|---------------------------------------------------------------------|
| **1. 学习 LangGraph 基础**：理解如何定义节点、边和状态转移，用于构建多 Agent 工作流。 | 已学习并使用 LangGraph 构建完整流程，包含四个节点（RAG → SPARQL → Analysis → Answer），支持状态传递与分支逻辑。 |
| **2. 学习 LangChain 核心模块**：掌握 PromptTemplate、Tool、Agent 的用法，用于自定义组件。 | 已在 RAG Agent 中实现 prompt 模板控制、DeepSeek 调用和嵌入检索逻辑。                    |
| **3. 实现 RAG 查询**：从 Brick Schema 与时间序列数据中检索信息。 | 已构建 FAISS 向量索引，结合 DeepSeek 生成 SPARQL；Brick 提供语义结构，CSV 提供时序数据。       |
| **4. 构建数据分析 Agent**：处理查询结果，执行平均值、极值、分组或趋势分析。 | Analysis Agent 已初步实现平均、最高、最低、趋势四种分析方式，可自动识别不同传感类型。                  |
| **5. 构建多 Agent 工作流**：使用 LangGraph 将 RAG 与分析 Agent 串联成完整管线。 | 已实现完整工作流，LangGraph 自动管理执行顺序与数据流。                                    |
| **6. 自然语言演示**：通过自然语言问题验证系统效果。 | 已测试中英文混合提问，涵盖温湿度、光强、噪声等多类型问题。                                       |

---

## 三、系统结构

```
自然语言问题
   │
   ▼
[RAG Agent]  —— 从 Brick TTL 检索上下文（FAISS）→ DeepSeek 生成 SPARQL
   │
   ▼
[SPARQL Agent] —— 使用 rdflib 在 Brick 图谱上执行查询 → 获取传感器/ts_id
   │
   ▼
[Analysis Agent] —— 根据 ts_id 访问 CSV，执行均值/极值/趋势分析
   │
   ▼
[Answer Agent] —— 将结果转化为自然语言（中英双语，含单位和日期）
```
---

## 四、模块说明

| 模块 | 主要功能 |
|------|-----------|
| `app/main_graph.py` | 程序入口，定义 LangGraph 工作流与命令行接口。 |
| `app/graph.py` | 定义节点关系：`rag → sparql → analysis → answer`。 |
| `app/nodes/rag_agent.py` | 构建向量索引，检索 Brick 上下文，调用 DeepSeek 生成 SPARQL。 |
| `app/nodes/sparql_agent.py` | 执行 SPARQL 查询，返回 RDF 结果（传感器、类型、ts_id 等）。 |
| `app/nodes/analysis_agent.py` | 读取 CSV，计算平均值、最高/最低值、趋势变化等指标。 |
| `app/nodes/answer_agent.py` | 将结果包装为自然语言回答，自动识别单位与语义类型。 |

---

## 五、数据结构

- **`data/site_generated.ttl`**
  模拟建筑知识图谱，符合 Brick Schema。
  ```
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    @prefix bldg:  <http://example.com/building#> .
    @prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
    
    
    bldg:Room_1 a brick:Room ;
        rdfs:label "Room 1" ;
        brick:hasPoint bldg:Temp_Sensor_1 , bldg:Humi_Sensor_1 , bldg:Lux_Sensor_1 , bldg:Noise_Sensor_1 , bldg:Light_Switch_1 , bldg:HVAC_Switch_1 .
    
    bldg:Temp_Sensor_1 a brick:Temperature_Sensor ;
        rdfs:label "Room 1 Temp Sensor" ;
        bldg:ts_id "room1_temp" .
    
    bldg:Humi_Sensor_1 a brick:Humidity_Sensor ;
        rdfs:label "Room 1 Humi Sensor" ;
        bldg:ts_id "room1_humi" .
    
    bldg:Lux_Sensor_1 a brick:Illuminance_Sensor ;
        rdfs:label "Room 1 Lux Sensor" ;
        bldg:ts_id "room1_lux" .
    
    bldg:Noise_Sensor_1 a brick:Noise_Sensor ;
        rdfs:label "Room 1 Noise Sensor" ;
        bldg:ts_id "room1_noise" .
    
    bldg:Light_Switch_1 a brick:On_Off_Command ;
        rdfs:label "Room 1 Light Switch" ;
        bldg:ts_id "room1_light_switch" .
    
    bldg:HVAC_Switch_1 a brick:On_Off_Command ;
        rdfs:label "Room 1 HVAC Switch" ;
        bldg:ts_id "room1_hvac_switch" .
    ……
  ```

- **`data/telemetry_generated.csv`**
  模拟时间序列数据，支持温度、湿度、光照、噪声四类。
  ```
    2025-10-16T00:00:00,room1_temp,21.07
    2025-10-16T00:00:00,room1_humi,52.39
    2025-10-16T00:00:00,room1_lux,27.84
    2025-10-16T00:00:00,room1_noise,63.27
    2025-10-16T00:00:00,room1_light_switch,0.0
    2025-10-16T00:00:00,room1_hvac_switch,0.0
    ……
  ```

---

## 六、运行示例

详情参考Research log.pdf的最后一页

| 输入 | 输出 |
|------|---------|
| Room 2 昨天的最低噪声是多少？ | 2025-10-16：最低噪声 35.20 dB（样本 24 条）。 |
| RRoom 3 昨儿个的最高、最低光强分别是多少？ | 2025-10-16：最高数值 578.79，最低数值 11.60（样本 24 条）。 |
| What is the average humidity of Room 4 yesterday? | 2025-10-16：平均湿度 45.60 %RH（样本 24 条）。 |
| Room 1 最近的温度趋势如何？ | 2025-10-16：趋势：基本稳定（样本 24 条）。 |
---

## 期待您的回复！