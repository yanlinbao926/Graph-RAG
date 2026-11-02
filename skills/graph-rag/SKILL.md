---
name: graph-rag
description: 基于确定性知识图谱的代码故障排查与精准溯源定位技能。当代码报错、抛出异常、运行时报错、功能逻辑异常、或者需要排查某个函数/模块为什么出错时触发。该技能通过本地 AST 知识图谱（Graph-RAG）对报错符号进行拓扑溯源，快速锁定精确代码文件与行号，并分析上游调用源与下游依赖，彻底避免全代码库盲目检索（No Blind Grepping）。
---

# Graph-Guided Debugger (图谱导航排查技能)

本技能基于本地 AST 确定性知识图谱引擎，为代码调试与故障修复提供**精准靶向定位（Precision Diagnosis）**。
核心理念：**“先查图谱定靶心，再看局部治病根，绝不全库盲目搜”**。

---

## 触发场景 (When to Use)

当遇到以下情况时，必须启动本技能：
1. 用户提供一段报错堆栈（Traceback / Exception / 500 错误）；
2. 用户提出某个业务流程或接口逻辑未按预期运行（如“报表生成失败”、“上传文件后没反应”）；
3. 需要修改某个核心函数，但不确定有哪些地方依赖它（影响面评估 / 爆炸半径分析）；
4. 用户提到“代码出问题了”、“帮我看看哪里坏了”、“排查这个 bug”。

---

## 核心排查流水线 (Workflow Steps)

```
[报错/异常线索] ➔ 1. 图谱构建/加载 ➔ 2. 拓扑靶向溯源 (上下游调用) ➔ 3. 精准代码审计 ➔ 4. 影响面评估与修复
```

### 第一步：确保本地知识图谱已就绪 (Build / Load Graph)

在排查前，先确认本地是否有最新的知识图谱。若未生成或代码刚发生过重大改动，执行极速本地扫描（0 API 开销，秒级完成）：

```bash
# 扫描本地代码库并输出拓扑
python -m graph_rag . --output ./graph_rag_out
```

### 第二步：提取异常符号，执行拓扑溯源 (Topological Tracing)

从报错信息、URL 路由、或用户描述中提取核心符号（函数名、类名、变量名或报错文件）。
调用内置的图谱查询工具获取故障节点的上下游关系：

```bash
python .config/opencode/skills/graph-rag/scripts/query_graph.py "<报错符号或函数名>" --graph ./graph_rag_out/graph.json
```

**分析输出的核心数据：**
1. **精确坐标**：确定该符号所在的文件相对路径与精确行号（`path:line`）；
2. **上游调用源（In-degree Callers）**：是谁调用了发生异常的函数？（往往“报错的那一行是受害者，真正传错参数的罪魁祸首在上游”）；
3. **下游依赖（Out-degree Callees）**：它调用的底层组件是否为空、是否未初始化；
4. **God Node 警示**：如果该节点度数极高（God Node），说明是系统主干，修改时不能随意改变函数签名或返回值结构。

### 第三步：靶向深入代码与日志审计 (Precision Code Audit)

根据第二步锁定的 `path:line`，**仅读取**相关的目标文件（通常只需查看 1~2 个文件局部切片，而非全库 Grep）：

- **检查直接受害点**：目标函数内的变量判空、类型转换、边界条件；
- **检查上游调用方**：参数是否透传正确，是否有异步等待缺失；
- **服务器位置对齐**：如果是远程环境部署，直接定位到服务器对应路径 `/home/deploy/annual-report-app/<path>`，核对环境差异。

### 第四步：爆炸半径评估与最小化安全修复 (Blast Radius Check)

在生成修复代码之前，利用图谱做一次“防破坏”检查：
- 确认修改后是否会破坏图谱中已知的其他调用方；
- 遵循最小修改原则（Minimal Intervention），保留现有接口兼容性；
- 严禁触碰任何网络端路由与既定架构。

---

## 示例实战流程 (Example)

**用户输入：**
> “运行报表生成时，`DataAnalysisEngine` 报错了，提示找不到 sheet 或列名不存在，帮我看看哪里坏了。”

**Skill 执行动作：**
1. 执行图谱查询：
   ```bash
   python .config/opencode/skills/graph-rag/scripts/query_graph.py "DataAnalysisEngine"
   ```
2. 得到拓扑反馈：
   - 目标位于 `app/services/data_engine.py:18`；
   - 上游调用方来自 `workflows/report_generator.py:45` 和 `agent/tool_registry.py:120`；
3. 直接读取 `app/services/data_engine.py` 与 `workflows/report_generator.py` 的调用点，发现调用方传入了未清洗的别名；
4. 完成修复，并向用户汇报上下游链路闭环。
