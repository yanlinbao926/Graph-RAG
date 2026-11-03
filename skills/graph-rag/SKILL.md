---
name: graph-rag
description: 基于确定性知识图谱的代码故障排查、架构理解与精准溯源定位技能。适用于任何 Python 或通用软件项目。当代码报错抛出异常、业务链路异常、需要理解架构拓扑、或修改核心代码需评估爆炸半径（上下游影响面）时触发。该技能通过本地 AST 确定性知识图谱（Graph-RAG）对目标符号进行拓扑溯源，快速锁定精确代码坐标（文件与行号），并分析上游调用源与下游依赖，彻底避免全代码库盲目检索（No Blind Grepping）。
---

# Graph-Guided Debugger (通用图谱导航与精准定位技能)

本技能基于本地 AST 确定性知识图谱引擎，为**任意软件工程项目**的代码理解、调用链路追踪、架构审计与故障排查提供**精准靶向定位（Precision Diagnosis）**。
核心理念：**“先查图谱定靶心，再看局部治病根，绝不全库盲目搜”**。

---

## 适用场景 (When to Use)

本技能适用于任何需要深入理解或调试代码拓扑的通用软件项目，在遇到以下场景时触发：
1. **异常堆栈与错误排查**：收到报错堆栈（Traceback / Exception / 500 / 运行时错误），需快速定位根因；
2. **业务调用链异常**：业务链路执行不符合预期，需要追踪上游请求究竟经过哪些组件传递到底层；
3. **安全重构与爆炸半径评估 (Blast Radius)**：准备修改核心函数、类或公共接口时，必须先评估所有直接与间接调用方；
4. **两点调用路径探查 (A ➔ B Path)**：需要理清两个看似独立的模块或接口之间是如何逐级串联调用的；
5. **代码库架构快速上手**：新接触某个陌生项目，需要理清系统核心中枢（God Nodes）与模块社区边界。

---

## 核心工作流 (Workflow Steps)

```
[排查/分析线索] ➔ 1. 构建/加载图谱 ➔ 2. 拓扑靶向溯源 (单点诊断 / 两点穿透) ➔ 3. 局部精准代码审计 ➔ 4. 影响面评估与安全处理
```

### 第一步：确保本地知识图谱已就绪 (Build / Load Graph)

在排查或分析前，确认当前项目目录下是否已有生成的知识图谱。若未生成或代码刚发生过改动，执行极速本地扫描（0 API Token 开销，秒级完成）：

```bash
# 扫描当前项目根目录代码库并输出拓扑产物
python -m graph_rag . --output ./graph_rag_out
```

### 第二步：执行拓扑靶向溯源与链路穿透 (Topological Tracing)

从报错信息、日志提示、API 路由或任务目标中提取核心符号（函数名、类名、方法名或接口名）。
调用内置图谱分析脚本获取拓扑关系：

#### 模式 1：单点符号深度诊断 (上下游调用源与爆炸半径评估)
```bash
python .config/opencode/skills/graph-rag/scripts/query_graph.py "<目标符号或函数名>" --graph ./graph_rag_out/graph.json
```

**分析输出的核心指标：**
1. **精确代码坐标**：返回该符号所在的文件相对路径与精确定义行号（`path:line`）；
2. **上游调用源（In-degree Callers）**：是谁调用了该节点？（多数情况下，抛出异常的那一行只是受害者，传递错误参数或逻辑缺陷的根因在上游调用方）；
3. **下游依赖（Out-degree Callees）**：它进一步调用了哪些底层组件与辅助方法；
4. **系统核心节点警示（God Node Alert）**：若该节点度数（Degree）极高，表明它是系统的核心公共骨干，修改时必须保持向后兼容，严禁破坏接口签名。

#### 模式 2：任意两点调用路径穿透 (A ➔ B Shortest Execution Path)
当需要探查某入口端点（API Controller / CLI Command）如何一步步调用到底层服务或组件时：
```bash
python .config/opencode/skills/graph-rag/scripts/query_graph.py "<起点A>" "<终点B>" --graph ./graph_rag_out/graph.json
```

**输出示例：**
```text
✨ [Shortest Path Found]: 3 hops (Zero files opened)
  #0 [function] api_server:handle_request (api/server.py:42)
     ── ⚡ calls (L56) ──>
  #1 [method] order_service:OrderService.create_order (services/order.py:118)
     ── ⚡ calls (L142) ──>
  #2 [method] payment_client:PaymentClient.process_charge (clients/payment.py:75)
     ── ⚡ calls (L88) ──>
  #3 [function] http_utils:send_request (utils/http.py:20)
```

### 第三步：靶向深入代码切片审计 (Precision Code Audit)

根据图谱返回的精确 `path:line`，**仅定位阅读**涉事模块的局部实现代码（通常仅需阅读 1~2 个文件的关键上下文，彻底告别盲目全库 Grep）：

- **受害点检查**：目标函数内部入参校验、判空逻辑、类型转换与异常分支；
- **上游来源核对**：检查直接上游调用方在调用传参时是否存在数据格式不一致、未捕获异常或异步等待缺失；
- **配置与依赖对齐**：核对调用的底层外部组件或环境配置是否初始化完整。

### 第四步：爆炸半径检查与最小化安全变更 (Blast Radius Check)

在生成任何修复或重构代码之前，利用图谱关系做一次“防破坏”检查：
- 确认修改函数签名、返回值或逻辑行为时，是否会影响到图谱中已被标记的其他调用方（In-degree nodes）；
- 遵循最小修改原则（Minimal Intervention），优先在局部做容错与兼容处理；
- 避免对无关业务链路产生非预期的副作用。

---

## 典型排查实战范例 (Example)

**场景输入：**
> “调用接口处理订单时报了 `TypeError: missing required argument` 异常，符号提示为 `process_transaction`，帮我排查原因。”

**Skill 标准执行流程：**
1. **拓扑查询**：
   ```bash
   python .config/opencode/skills/graph-rag/scripts/query_graph.py "process_transaction"
   ```
2. **图谱返回拓扑事实**：
   - 目标函数定义位于 `services/payment_service.py:85`；
   - 上游直接调用方为 `handlers/checkout_handler.py:140`；
   - 下游依赖为 `adapters/gateway_adapter.py:32`。
3. **靶向代码审计**：
   - 直接读取 `handlers/checkout_handler.py` 第 140 行附近的上下文，发现上游在重构时遗漏了新增的 `currency` 必填参数；
4. **安全闭环修复**：
   - 检查 `process_transaction` 的所有入度调用方，确认修复该处上游传参后不影响其他调用链路，完成修复汇报。
