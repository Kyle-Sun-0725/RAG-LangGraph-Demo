# RAG-LangGraph Demo：基于 Brick Schema 的自然语言查询与数据分析系统

## 一、项目概述
本项目实现了一个**纯后端多智能体系统（multi-agent system）**，支持使用自然语言查询建筑信息与传感数据。  
系统以 **Brick Schema** 为语义基础，结合 **RAG（Retrieval-Augmented Generation）** 与 **LangGraph** 协同实现问答、查询与分析全流程。

---

## 二、系统架构

```
自然语言问题
   │
   ▼
[RAG Agent] —— 从 Brick TTL 检索上下文（FAISS）→ DeepSeek 生成 SPARQL
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

## 三、模块说明

| 模块                              | 功能 |
|---------------------------------|------|
| `app/main_graph.py`             | 程序入口，定义 LangGraph 工作流与命令行接口。 |
| `app/graph.py`                  | 定义节点关系：`rag → sparql → analysis → answer`。 |
| `app/nodes/rag_agent.py`        | 检索 Brick 上下文，调用 DeepSeek 生成 SPARQL 查询。 |
| `app/nodes/sparql_agent.py`     | 执行 SPARQL 查询，获取 RDF 结果（传感器、类型、ts_id 等）。 |
| `app/nodes/analysis_agent.py`   | 从 CSV 读取时间序列，计算平均值、最高/最低值、趋势。 |
| `app/nodes/answer_agent.py`     | 将结果包装为自然语言回答，自动识别单位与语义类型。 |
| `app/nodes/sparql_exec.py`      | 统一的 SPARQL 执行入口：封装 rdflib 查询并返回表格化结果。 |
| `app/tools/brick_store.py`      | 加载并缓存 Brick RDF 图谱（site_generated.ttl），提供 Graph 查询能力。  |
| `data_generator/data_generator.py` | 自动生成 Brick TTL 与时序 CSV，用于可复现实验。 |

---

## 四、数据结构

### `data/site_generated.ttl`
符合 Brick Schema 的建筑知识图谱：

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

### `data/telemetry_generated.csv`
模拟时间序列数据（温度、湿度、光照、噪声等）：

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

## 五、运行说明

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```
2. **刷新测试数据集**
   ```bash
   python data_generator/data_generator.py
   ```
   
3. **运行主程序**
   ```bash
   python app/main_graph.py
   ```

4. **示例交互**
   ```
   You: Room 3 昨天的平均温度是多少？
   [ANSWER] 2025-10-16：平均温度 22.62 °C。

   You: Room 2 昨天的最低噪声是多少？
   [ANSWER] 2025-10-16：最低噪声 35.20 dB（样本 24 条）。
   ```

---

## 六、结果展示

| 输入 | 输出 |
|------|------|
| Room 2 昨天的最低噪声是多少？ | 2025-10-16：最低噪声 35.20 dB（样本 24 条）。 |
| Room 3 昨儿个的最高、最低光强分别是多少？ | 2025-10-16：最高 578.79，最低 11.60（样本 24 条）。 |
| What is the average humidity of Room 4 yesterday? | 2025-10-16：平均湿度 45.60 %RH（样本 24 条）。 |
| Room 1 最近的温度趋势如何？ | 2025-10-16：趋势：基本稳定（样本 24 条）。 |

---

## 七、说明

- 所有数据均为自动生成的模拟数据，用于复现系统逻辑。  
- 系统支持中英文自然语言查询与结果生成。  
- 后端基于LangGraph构建，可扩展更多功能节点。

---

## License

This project is licensed under the MIT License.

---
