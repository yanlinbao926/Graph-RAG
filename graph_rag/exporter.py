"""
Graph-RAG 多模态导出与报告生成引擎 (Export & Reporting)
生成产物：
1. graph.json: 工业标准 Node-Link 格式 (100% 兼容 NetworkX / D3 / Neo4j)
2. GRAPH_REPORT.md: 结构化 Markdown 架构见解全景报告
3. graph.mermaid: 快速嵌入文档或被 AI 上下文读取的 Mermaid 拓扑图
4. graph.html: 支持 2D 力导向 / 3D 宇宙球体围绕旋转、深层多跳调用链追踪、边类型过滤的交互系统 (0 外部网络请求)
"""

import json
import os
from typing import List, Dict, Any
from .models import Node, Edge, CommunityInfo, TopologyInsight
from .graph_builder import Graph


class GraphExporter:
    """导出与报告生成器"""

    def __init__(self, graph: Graph, communities: List[CommunityInfo], insights: TopologyInsight):
        self.graph = graph
        self.communities = communities
        self.insights = insights

    def export_all(self, output_dir: str) -> Dict[str, str]:
        """将所有格式导出到指定目录并返回生成的文件路径映射"""
        os.makedirs(output_dir, exist_ok=True)
        paths = {
            "json": os.path.join(output_dir, "graph.json"),
            "report": os.path.join(output_dir, "GRAPH_REPORT.md"),
            "mermaid": os.path.join(output_dir, "graph.mermaid"),
            "html": os.path.join(output_dir, "graph.html")
        }

        self.export_node_link_json(paths["json"])
        self.export_markdown_report(paths["report"])
        self.export_mermaid(paths["mermaid"])
        self.export_standalone_html(paths["html"])

        return paths

    def export_node_link_json(self, output_path: str):
        """导出为 Node-Link 规范 JSON"""
        data = {
            "directed": True,
            "multigraph": False,
            "graph": {
                "name": "Graph-RAG Knowledge Graph",
                "total_nodes": len(self.graph.nodes),
                "total_edges": len(self.graph.edges),
                "communities_count": len(self.communities)
            },
            "nodes": [node.to_dict() for node in self.graph.nodes.values()],
            "links": [edge.to_dict() for edge in self.graph.edges]
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_markdown_report(self, output_path: str):
        """生成 GRAPH_REPORT.md 架构与知识洞察报告"""
        md = []
        md.append("# 🌐 Graph-RAG 确定性代码知识图谱诊断报告 (GRAPH_REPORT)\n")
        md.append("> 本报告基于本地 AST 确定性语法树提取与图拓扑算法生成，无需向量数据库，无网络/Token 开销。\n")

        # 1. 核心指标概览
        md.append("## 📊 1. 核心拓扑指标概览\n")
        md.append(f"- **总节点数 (Nodes)**: `{self.insights.total_nodes}`")
        md.append(f"- **总边数 (Edges / Relations)**: `{self.insights.total_edges}`")
        md.append(f"- **独立架构子系统社区数 (Leiden Clusters)**: `{len(self.communities)}`")
        
        conf_dist = self.insights.confidence_distribution
        md.append(f"- **关系置信度分布 (Confidence Tagging)**:")
        md.append(f"  - `EXTRACTED` (确定性 AST 提取, 1.0): **{conf_dist.get('EXTRACTED', 0)}** 处")
        md.append(f"  - `INFERRED` (符号与上下文推导, 0.55~0.95): **{conf_dist.get('INFERRED', 0)}** 处")
        md.append(f"  - `AMBIGUOUS` (多义性候选, 需关注): **{conf_dist.get('AMBIGUOUS', 0)}** 处\n")

        # 2. 上帝中枢节点 (God Nodes)
        md.append("## 👑 2. 核心中枢节点 (God Nodes)\n")
        md.append("度中心性最高的核心枢纽，系统的架构骨干：\n")
        md.append("| 节点 ID | 名称 | 类型 | 路径 | 度数 (入度/出度) | 所属社区 |")
        md.append("|---|---|---|---|---|---|")
        for g in self.insights.god_nodes:
            md.append(f"| `{g['id']}` | **{g['name']}** | `{g['kind']}` | `{g['path']}` | `{g['degree']}` ({g['in_degree']}/{g['out_degree']}) | Cluster #{g['community_id']} |")
        md.append("\n")

        # 3. 架构子系统社区划分 (Leiden Clusters)
        md.append("## 🧩 3. 架构子系统社区划分 (Leiden Subsystems)\n")
        md.append("| 社区编号 | 子系统命名 | 规模 (节点数) | 内部凝聚密度 | 领导核心节点 |")
        md.append("|---|---|---|---|---|")
        for comm in self.communities:
            leads = ", ".join([f"`{n.split(':')[-1]}`" for n in comm.central_nodes])
            md.append(f"| #{comm.community_id} | **{comm.name}** | {comm.size} | `{comm.internal_density}` | {leads} |")
        md.append("\n")

        # 4. 意外跨界连接 (Surprising Connections)
        md.append("## ⚡ 4. 意外跨界连接 (Surprising Connections)\n")
        md.append("跨越不同架构社区的长依赖关系（暴露潜在的跨层耦合或关键桥接通道）：\n")
        if self.insights.surprising_connections:
            md.append("| 源组件 (社区) | 目标组件 (社区) | 关系类型 | 置信度 | 解析说明 |")
            md.append("|---|---|---|---|---|")
            for c in self.insights.surprising_connections:
                md.append(f"| `{c['source_name']}` (#{c['source_community']}) | `{c['target_name']}` (#{c['target_community']}) | `{c['kind']}` | `{c['confidence']}` | {c['explanation']} |")
        else:
            md.append("未发现显著的异常跨社区高危耦合。")
        md.append("\n")

        # 5. 循环依赖诊断 (Cycles)
        md.append("## 🔄 5. 循环依赖诊断 (Circular Dependencies)\n")
        if self.insights.cycles:
            md.append("⚠️ **警告：检测到拓扑环路**，可能导致模块初始化冲突或高强耦合：\n")
            for idx, cycle in enumerate(self.insights.cycles, start=1):
                cycle_str = " ➔ ".join([f"`{node.split(':')[-1]}`" for node in cycle])
                md.append(f"- **环路 #{idx}**: {cycle_str}")
        else:
            md.append("✅ **健康**: 经有向拓扑检测，未发现静态调用与导入环路。")
        md.append("\n")

        # 6. 未引用与孤儿节点 (Orphan Nodes)
        md.append("## 👻 6. 潜在冗余与代码盲区 (Orphan Nodes)\n")
        if self.insights.orphan_nodes:
            md.append("| 节点 ID | 名称 | 类型 | 路径 | 行号 |")
            md.append("|---|---|---|---|---|")
            for o in self.insights.orphan_nodes:
                md.append(f"| `{o['id']}` | `{o['name']}` | `{o['kind']}` | `{o['path']}` | {o['line']} |")
        else:
            md.append("所有符号与组件均具有有效引用。")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

    def export_mermaid(self, output_path: str):
        """生成 Mermaid 图谱文件"""
        lines = ["flowchart TD"]
        # 为防止 Mermaid 过载，选择前 60 条核心边
        core_edges = sorted(
            self.graph.edges,
            key=lambda e: (
                self.graph.nodes.get(e.source, Node("", "", "", "")).degree +
                self.graph.nodes.get(e.target, Node("", "", "", "")).degree
            ),
            reverse=True
        )[:60]

        def safe_id(nid: str) -> str:
            return "n_" + "".join(c if c.isalnum() else "_" for c in nid)

        for e in core_edges:
            s_node = self.graph.nodes.get(e.source)
            t_node = self.graph.nodes.get(e.target)
            if not s_node or not t_node:
                continue

            s_id = safe_id(e.source)
            t_id = safe_id(e.target)

            s_lbl = f"{s_node.name}\\n({s_node.kind.value})"
            t_lbl = f"{t_node.name}\\n({t_node.kind.value})"

            arrow = "-->"
            if e.kind.value == "calls":
                arrow = "-- calls -->"
            elif e.kind.value == "imports":
                arrow = "-- imports -->"
            elif e.kind.value == "defines":
                arrow = "-- defines -->"

            lines.append(f"    {s_id}[\"{s_lbl}\"] {arrow} {t_id}[\"{t_lbl}\"]")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def export_standalone_html(self, output_path: str):
        """生成支持 2D/3D 双模围绕旋转、深层调用链路追踪、边类型过滤的交互页面"""
        nodes_payload = []
        for n in self.graph.nodes.values():
            nodes_payload.append({
                "id": n.id,
                "name": n.name,
                "kind": n.kind.value if hasattr(n.kind, "value") else str(n.kind),
                "path": n.path,
                "line": n.line,
                "comm": n.community_id,
                "deg": n.degree,
                "in_deg": n.in_degree,
                "out_deg": n.out_degree,
                "doc": (n.docstring or "").strip().split("\n")[0][:100]
            })

        edges_payload = []
        for e in self.graph.edges:
            edges_payload.append({
                "s": e.source,
                "t": e.target,
                "k": e.kind.value if hasattr(e.kind, "value") else str(e.kind),
                "c": e.confidence.value if hasattr(e.confidence, "value") else str(e.confidence)
            })

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Graph-RAG 知识图谱探索器 (2D/3D 立体旋转 & 深度链路追踪)</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #07090e; color: #f1f5f9; display: flex; height: 100vh; overflow: hidden; user-select: none; }}
  #sidebar {{ width: 330px; background: rgba(15, 18, 25, 0.95); border-right: 1px solid rgba(255,255,255,0.08); padding: 1.1rem; display: flex; flex-direction: column; gap: 0.85rem; overflow-y: auto; z-index: 10; backdrop-filter: blur(12px); }}
  #canvas-container {{ flex: 1; position: relative; width: 100%; height: 100%; overflow: hidden; background: radial-gradient(circle at 50% 50%, #0f1322 0%, #050609 100%); }}
  canvas {{ width: 100%; height: 100%; display: block; cursor: grab; }}
  canvas:active {{ cursor: grabbing; }}
  h1 {{ font-size: 1.05rem; color: #38bdf8; display: flex; align-items: center; gap: 0.45rem; }}
  .badge {{ font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; background: rgba(56,189,248,0.12); color: #38bdf8; border: 1px solid rgba(56,189,248,0.25); }}
  .stat-card {{ background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 0.65rem 0.8rem; font-size: 0.78rem; line-height: 1.6; }}
  .search-box {{ width: 100%; padding: 0.5rem 0.75rem; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; color: #fff; font-size: 0.82rem; outline: none; transition: border-color 0.2s; }}
  .search-box:focus {{ border-color: #38bdf8; }}
  
  /* 视图过滤器选择器 */
  .view-filter {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.35rem; }}
  .filter-btn {{ background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); color: #94a3b8; padding: 0.35rem 0.45rem; border-radius: 5px; font-size: 0.72rem; cursor: pointer; text-align: center; transition: all 0.2s; }}
  .filter-btn.active {{ background: rgba(56,189,248,0.15); color: #38bdf8; border-color: #38bdf8; font-weight: 600; }}
  
  .legend-item {{ display: flex; align-items: center; gap: 0.5rem; font-size: 0.73rem; color: #94a3b8; margin-top: 0.25rem; cursor: pointer; padding: 3px 5px; border-radius: 4px; transition: background 0.15s; }}
  .legend-item:hover {{ background: rgba(255,255,255,0.05); color: #f8fafc; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
  
  /* 悬停浮窗 */
  #tooltip {{ position: absolute; display: none; pointer-events: none; background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 6px; padding: 0.55rem 0.75rem; font-size: 0.75rem; color: #f1f5f9; box-shadow: 0 8px 24px rgba(0,0,0,0.7); z-index: 100; max-width: 320px; backdrop-filter: blur(10px); }}
  
  /* 浮动操作控制器 (右上角/右下角) */
  .hud-top-controls {{ position: absolute; top: 1.2rem; right: 1.2rem; display: flex; gap: 0.5rem; z-index: 20; }}
  .hud-bottom-controls {{ position: absolute; bottom: 1.2rem; right: 1.2rem; display: flex; gap: 0.45rem; z-index: 20; }}
  .hud-btn {{ background: rgba(26, 33, 48, 0.88); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.14); padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.75rem; cursor: pointer; transition: all 0.2s; backdrop-filter: blur(8px); display: flex; align-items: center; gap: 0.35rem; }}
  .hud-btn:hover {{ background: #334155; color: #fff; border-color: #38bdf8; }}
  .hud-btn.active {{ background: #0284c7; color: #fff; border-color: #38bdf8; font-weight: 600; box-shadow: 0 0 12px rgba(2,132,199,0.5); }}

  /* 多跳调用路径追踪条目 */
  .chain-node {{ padding: 3px 6px; border-radius: 4px; background: rgba(56,189,248,0.08); border-left: 2px solid #38bdf8; margin: 3px 0; font-family: monospace; font-size: 0.72rem; cursor: pointer; }}
  .chain-node:hover {{ background: rgba(56,189,248,0.2); color: #fff; }}
</style>
</head>
<body>
  <div id="sidebar">
    <div>
      <h1>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
        Graph-RAG 拓扑探索器
      </h1>
      <span class="badge" style="margin-top:0.35rem; display:inline-block;">3D 旋转围绕 · 深度调用链延伸追踪</span>
    </div>

    <!-- 视图模式过滤 -->
    <div>
      <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:0.35rem; font-weight:500;">拓扑视图模式</div>
      <div class="view-filter">
        <button class="filter-btn active" id="btnFilterAll" onclick="setEdgeFilter('all')">全景架构 (All)</button>
        <button class="filter-btn" id="btnFilterCalls" onclick="setEdgeFilter('calls')" title="隐藏文件包含边，专门展现纵向调用链条延伸">⚡ 深层调用链流</button>
        <button class="filter-btn" id="btnFilterImports" onclick="setEdgeFilter('imports')">📦 模块依赖</button>
        <button class="filter-btn" id="btnFilterDefines" onclick="setEdgeFilter('defines')">🌲 源码归属</button>
      </div>
    </div>

    <!-- 节点模糊搜索 -->
    <input type="text" id="searchInput" class="search-box" placeholder="🔍 快速搜索函数、类、模块、文件名...">

    <!-- 任意两点最短路径追踪控制器 (graph-rag path UI) -->
    <div class="stat-card" style="border-color: rgba(245,158,11,0.3); background: rgba(245,158,11,0.04);">
      <div style="font-weight:600; color:#f59e0b; font-size:0.75rem; margin-bottom:0.4rem; display:flex; justify-content:space-between;">
        <span>📍 任意两点调用路径穿透</span>
        <span style="font-size:0.68rem; color:#94a3b8;">A ➔ B 穿透</span>
      </div>
      <div style="display:flex; flex-direction:column; gap:0.35rem;">
        <input type="text" id="pathSourceInput" class="search-box" placeholder="起点 A: 如 main 或 standalone_chat" style="padding:0.38rem 0.6rem; font-size:0.75rem;">
        <input type="text" id="pathTargetInput" class="search-box" placeholder="终点 B: 如 robust_read_excel 或 Docx" style="padding:0.38rem 0.6rem; font-size:0.75rem;">
        <div style="display:flex; gap:0.35rem; margin-top:2px;">
          <button class="filter-btn active" style="flex:1; background:rgba(245,158,11,0.2); border-color:#f59e0b; color:#f59e0b; font-weight:bold;" onclick="triggerShortestPath()">⚡ 穿透连线</button>
          <button class="filter-btn" style="flex:0.6;" onclick="clearPathTrace()">清除</button>
        </div>
      </div>
      <div id="pathResultBox" style="display:none; margin-top:0.45rem; font-size:0.72rem; line-height:1.5; color:#cbd5e1; border-top:1px dashed rgba(255,255,255,0.1); padding-top:0.35rem;">
      </div>
    </div>

    <!-- 概览面板 -->
    <div class="stat-card">
      <div style="display:flex; justify-content:space-between;">
        <span>实体节点: <strong style="color:#38bdf8;">{len(self.graph.nodes)}</strong></span>
        <span>当前连线: <strong style="color:#34d399;" id="visibleEdgesCount">{len(self.graph.edges)}</strong></span>
      </div>
      <div>3D 控制: <strong>鼠标左键拖拽旋转</strong> / <strong>滚轮缩放</strong> / <strong>右键平移</strong></div>
    </div>

    <!-- 节点详情 / 多跳链条面板 -->
    <div id="nodeDetails" class="stat-card" style="display:none; border-color: rgba(56,189,248,0.4); background: rgba(15,23,42,0.7);">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:600; color:#38bdf8; font-size:0.82rem;" id="detName">组件名称</span>
        <button onclick="clearSelection()" style="background:transparent; border:none; color:#94a3b8; cursor:pointer; font-size:0.8rem;">&times;</button>
      </div>
      <div style="font-size:0.73rem; color:#cbd5e1; margin-top:2px;" id="detKind">类型</div>
      <div style="font-size:0.7rem; color:#64748b; word-break:break-all; margin-top:2px;" id="detPath">路径</div>
      <div style="font-size:0.72rem; color:#34d399; margin-top:3px;" id="detDeg">度数</div>

      <!-- 多跳调用链延伸追踪 -->
      <div style="margin-top: 0.6rem; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 0.45rem;">
        <div style="font-weight:600; color:#f59e0b; font-size:0.74rem; margin-bottom:0.25rem;">
          🔗 纵向多级调用链路延伸 (Multi-Hop)
        </div>
        <div id="downstreamChainList" style="max-height: 120px; overflow-y: auto;">
          <span style="color:#64748b; font-size:0.7rem;">(点击节点计算下游延伸)</span>
        </div>
      </div>
    </div>

    <!-- 社区分布 -->
    <div class="stat-card" style="flex: 1; overflow-y: auto;">
      <div style="font-weight:600; margin-bottom:0.4rem; color:#e2e8f0; display:flex; justify-content:space-between;">
        <span>社区子系统 (点击聚焦)</span>
        <span style="font-size:0.7rem; color:#64748b;">Top 10</span>
      </div>
      <div id="communityList">
        {"".join([f"<div class='legend-item' onclick='focusCommunity({c.community_id})'><span class='dot' style='background:hsl({(c.community_id * 67) % 360}, 75%, 55%);'></span><span style='white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>#{c.community_id} {c.name} ({c.size})</span></div>" for c in self.communities[:10]])}
      </div>
    </div>
  </div>

  <div id="canvas-container">
    <canvas id="graphCanvas"></canvas>
    <div id="tooltip"></div>

    <!-- 右上角：2D / 3D 视角切换 -->
    <div class="hud-top-controls">
      <button class="hud-btn" id="btnMode2D" onclick="switchDimension('2D')">2D 平面力导向</button>
      <button class="hud-btn active" id="btnMode3D" onclick="switchDimension('3D')">🪐 3D 立体宇宙星系 (围绕旋转)</button>
    </div>

    <!-- 右下角：导航与运动控制 -->
    <div class="hud-bottom-controls">
      <button class="hud-btn" onclick="zoomIn()" title="放大">➕ 放大</button>
      <button class="hud-btn" onclick="zoomOut()" title="缩小">➖ 缩小</button>
      <button class="hud-btn" onclick="resetView()" title="重置视角居中">🎯 复位视角</button>
      <button class="hud-btn" id="physicsToggleBtn" onclick="togglePhysics()" title="暂停/继续物理运动">⏸️ 暂停运动</button>
    </div>
  </div>

  <script>
    const rawNodes = {json.dumps(nodes_payload)};
    const rawEdges = {json.dumps(edges_payload)};

    const canvas = document.getElementById('graphCanvas');
    const ctx = canvas.getContext('2d');
    const tooltip = document.getElementById('tooltip');

    let width = 0, height = 0;
    let viewMode = '3D'; // '2D' or '3D'
    let currentEdgeFilter = 'all'; // 'all', 'calls', 'imports', 'defines'

    // 2D 变换
    let transform2D = {{ x: 0, y: 0, k: 1 }};
    
    // 3D 欧拉旋转角与平移
    let rotX = 0.25, rotY = -0.4;
    let cameraZ = 750;
    let pan3D = {{ x: 0, y: 0 }};

    // 交互拖拽状态
    let isMouseDown = false;
    let mouseButton = 0; // 0: left, 2: right
    let lastMouseX = 0, lastMouseY = 0;
    let draggedNode = null;
    let hoveredNode = null;
    let selectedNode = null;
    let activeCallChainNodes = new Set();
    let activeCallChainEdges = new Set();

    let physicsRunning = true;
    let alpha = 1.0;

    function resize() {{
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
      if (transform2D.x === 0 && transform2D.y === 0) {{
        transform2D.x = width / 2;
        transform2D.y = height / 2;
      }}
    }}
    window.addEventListener('resize', resize);
    resize();

    // 节点 3D/2D 空间初始化
    const nodeMap = new Map();
    const outgoingCallsMap = new Map(); // node_id -> [target_ids]
    const incomingCallsMap = new Map(); // node_id -> [source_ids]
    const allAdjMap = new Map();

    const nodes = rawNodes.map((n, i) => {{
      // 3D 球状斐波那契螺旋分布
      const phi = Math.acos(1 - 2 * (i + 0.5) / Math.max(1, rawNodes.length));
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      const sphereRadius = 260 + Math.random() * 180;

      const obj = {{
        ...n,
        // 3D 坐标
        x: sphereRadius * Math.sin(phi) * Math.cos(theta),
        y: sphereRadius * Math.sin(phi) * Math.sin(theta),
        z: sphereRadius * Math.cos(phi),
        vx: 0, vy: 0, vz: 0,
        // 投影渲染坐标
        projX: 0, projY: 0, projScale: 1, projZ: 0,
        radius: Math.min(18, Math.max(5, 3.5 + Math.sqrt(n.deg || 1) * 2.0)),
        color: `hsl(${{(n.comm * 67) % 360}}, 75%, 55%)`
      }};

      nodeMap.set(n.id, obj);
      outgoingCallsMap.set(n.id, []);
      incomingCallsMap.set(n.id, []);
      allAdjMap.set(n.id, new Set());
      return obj;
    }});

    const allEdges = [];
    for (const e of rawEdges) {{
      const source = nodeMap.get(e.s);
      const target = nodeMap.get(e.t);
      if (source && target && source !== target) {{
        const edgeObj = {{ source, target, kind: e.k, conf: e.c }};
        allEdges.push(edgeObj);
        allAdjMap.get(e.s).add(e.t);
        allAdjMap.get(e.t).add(e.s);

        if (e.k === 'calls') {{
          outgoingCallsMap.get(e.s).push(e.t);
          incomingCallsMap.get(e.t).push(e.s);
        }}
      }}
    }}

    let visibleEdges = [...allEdges];

    function setEdgeFilter(mode) {{
      currentEdgeFilter = mode;
      document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
      if (mode === 'all') document.getElementById('btnFilterAll').classList.add('active');
      if (mode === 'calls') document.getElementById('btnFilterCalls').classList.add('active');
      if (mode === 'imports') document.getElementById('btnFilterImports').classList.add('active');
      if (mode === 'defines') document.getElementById('btnFilterDefines').classList.add('active');

      if (mode === 'all') {{
        visibleEdges = allEdges;
      }} else {{
        visibleEdges = allEdges.filter(e => e.kind === mode);
      }}
      document.getElementById('visibleEdgesCount').innerText = visibleEdges.length;
      reheatPhysics(0.4);
    }}

    function switchDimension(mode) {{
      viewMode = mode;
      document.getElementById('btnMode2D').classList.toggle('active', mode === '2D');
      document.getElementById('btnMode3D').classList.toggle('active', mode === '3D');
      reheatPhysics(0.5);
    }}

    function reheatPhysics(val = 0.5) {{
      alpha = Math.max(alpha, val);
      if (!physicsRunning) {{
        physicsRunning = true;
        document.getElementById('physicsToggleBtn').innerText = '⏸️ 暂停运动';
        requestAnimationFrame(tick);
      }}
    }}

    // ==================== 任意两点最短路径追踪穿透 (graph-rag path A B) ====================
    let activePathChainNodes = new Set();
    let activePathChainEdges = new Set();

    function findNodeByKw(kw) {{
      if (!kw) return null;
      const kw_l = kw.toLowerCase().trim();
      for (const n of nodes) {{
        if (n.name.toLowerCase() === kw_l || n.id.toLowerCase() === kw_l) return n;
      }}
      for (const n of nodes) {{
        if (n.name.toLowerCase().includes(kw_l) || n.id.toLowerCase().includes(kw_l)) return n;
      }}
      return null;
    }}

    function triggerShortestPath() {{
      const srcText = document.getElementById('pathSourceInput').value.trim();
      const tgtText = document.getElementById('pathTargetInput').value.trim();
      const resBox = document.getElementById('pathResultBox');

      if (!srcText || !tgtText) {{
        resBox.style.display = 'block';
        resBox.innerHTML = '<span style="color:#ef4444;">请同时输入起点 A 与终点 B</span>';
        return;
      }}

      const srcNode = findNodeByKw(srcText);
      const tgtNode = findNodeByKw(tgtText);

      if (!srcNode) {{
        resBox.style.display = 'block';
        resBox.innerHTML = `<span style="color:#ef4444;">未在图谱中找到起点: "${{srcText}}"</span>`;
        return;
      }}
      if (!tgtNode) {{
        resBox.style.display = 'block';
        resBox.innerHTML = `<span style="color:#ef4444;">未在图谱中找到终点: "${{tgtText}}"</span>`;
        return;
      }}

      const queue = [[srcNode.id, [srcNode.id]]];
      const visited = new Set([srcNode.id]);
      let foundPath = null;

      while (queue.length > 0) {{
        const [currId, pathHistory] = queue.shift();
        if (currId === tgtNode.id) {{
          foundPath = pathHistory;
          break;
        }}

        const neighbors = allAdjMap.get(currId) || new Set();
        for (const nxtId of neighbors) {{
          if (!visited.has(nxtId)) {{
            visited.add(nxtId);
            queue.push([nxtId, pathHistory.concat([nxtId])]);
          }}
        }}
      }}

      activePathChainNodes.clear();
      activePathChainEdges.clear();

      if (!foundPath) {{
        resBox.style.display = 'block';
        resBox.innerHTML = `<span style="color:#f59e0b;">在图谱中两者未产生直接连通链路 (孤立子系统)</span>`;
        return;
      }}

      for (let i = 0; i < foundPath.length; i++) {{
        activePathChainNodes.add(foundPath[i]);
        if (i < foundPath.length - 1) {{
          activePathChainEdges.add(`${{foundPath[i]}}->${{foundPath[i+1]}}`);
          activePathChainEdges.add(`${{foundPath[i+1]}}->${{foundPath[i]}}`);
        }}
      }}

      const hops = foundPath.length - 1;
      resBox.style.display = 'block';
      const stepsHtml = foundPath.map((nid, idx) => {{
        const n = nodeMap.get(nid);
        const name = n ? n.name : nid.split(':').pop();
        return `<div class="chain-node" onclick="focusNode(nodeMap.get('${{nid}}'))"><strong style="color:#f59e0b;">#${{idx}}</strong> ${{name}}</div>`;
      }}).join('<div style="text-align:center; color:#10b981; font-weight:bold; font-size:0.68rem;">⬇ 穿透连线</div>');

      resBox.innerHTML = `
        <div style="color:#34d399; font-weight:bold; margin-bottom:4px;">✨ 最短连通路径 (${{hops}} 跳):</div>
        ${{stepsHtml}}
      `;

      const midX = (srcNode.x + tgtNode.x) / 2;
      const midY = (srcNode.y + tgtNode.y) / 2;
      if (viewMode === '3D') {{
        pan3D.x = -midX * 0.8;
        pan3D.y = -midY * 0.8;
        cameraZ = 650;
      }} else {{
        transform2D.k = 1.4;
        transform2D.x = width / 2 - midX * transform2D.k;
        transform2D.y = height / 2 - midY * transform2D.k;
      }}

      reheatPhysics(0.5);
    }}

    function clearPathTrace() {{
      activePathChainNodes.clear();
      activePathChainEdges.clear();
      document.getElementById('pathResultBox').style.display = 'none';
      document.getElementById('pathSourceInput').value = '';
      document.getElementById('pathTargetInput').value = '';
      reheatPhysics(0.2);
    }}

    // ==================== 多级多跳调用链延伸算法 ====================
    function traceCallChain(startNodeId) {{
      activeCallChainNodes.clear();
      activeCallChainEdges.clear();

      if (!startNodeId) return [];

      activeCallChainNodes.add(startNodeId);
      const chainEntries = [];
      const visited = new Set([startNodeId]);

      // 广度优先搜索 3 级深度的下游调用链路延伸
      const queue = [{{ id: startNodeId, depth: 0, path: [startNodeId] }}];

      while (queue.length > 0 && chainEntries.length < 15) {{
        const curr = queue.shift();
        if (curr.depth >= 4) continue;

        const nextTargets = outgoingCallsMap.get(curr.id) || [];
        for (const tid of nextTargets) {{
          activeCallChainNodes.add(tid);
          activeCallChainEdges.add(`${{curr.id}}->${{tid}}`);

          if (!visited.has(tid)) {{
            visited.add(tid);
            const targetNode = nodeMap.get(tid);
            const targetName = targetNode ? targetNode.name : tid.split(':').pop();
            const fullPathStr = curr.path.concat([tid]).map(x => (nodeMap.get(x)?.name || x.split(':').pop())).join(' ➔ ');

            chainEntries.push({{
              targetId: tid,
              depth: curr.depth + 1,
              name: targetName,
              pathText: fullPathStr
            }});

            queue.push({{ id: tid, depth: curr.depth + 1, path: curr.path.concat([tid]) }});
          }}
        }}
      }}

      // 向上追踪 1 级直接调用者 (Who calls me?)
      const upstreamCallers = incomingCallsMap.get(startNodeId) || [];
      for (const uid of upstreamCallers.slice(0, 5)) {{
        activeCallChainNodes.add(uid);
        activeCallChainEdges.add(`${{uid}}->${{startNodeId}}`);
      }}

      return chainEntries;
    }}

    // ==================== 物理动力学模拟 ====================
    function stepPhysics() {{
      if (alpha < 0.005) return;

      const springLength = viewMode === '3D' ? 70 : 85;
      const springK = 0.045 * alpha;
      const repulsion = (viewMode === '3D' ? 700 : 900) * alpha;

      // 1. 斥力
      for (let i = 0; i < nodes.length; i++) {{
        const a = nodes[i];
        if (a === draggedNode) continue;

        // 向原点微引力
        a.vx -= a.x * 0.015 * alpha;
        a.vy -= a.y * 0.015 * alpha;
        if (viewMode === '3D') a.vz -= a.z * 0.015 * alpha;

        for (let j = i + 1; j < nodes.length; j++) {{
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dz = viewMode === '3D' ? (b.z - a.z) : 0;
          const distSq = dx * dx + dy * dy + dz * dz || 1;

          if (distSq < 100000) {{
            const dist = Math.sqrt(distSq);
            const f = (repulsion / distSq);
            const fx = (dx / dist) * f;
            const fy = (dy / dist) * f;
            const fz = (dz / dist) * f;

            a.vx -= fx;
            a.vy -= fy;
            if (viewMode === '3D') a.vz -= fz;

            if (b !== draggedNode) {{
              b.vx += fx;
              b.vy += fy;
              if (viewMode === '3D') b.vz += fz;
            }}
          }}
        }}
      }}

      // 2. 弹簧引力
      for (const e of visibleEdges) {{
        const dx = e.target.x - e.source.x;
        const dy = e.target.y - e.source.y;
        const dz = viewMode === '3D' ? (e.target.z - e.source.z) : 0;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
        const f = (dist - springLength) * springK;

        const fx = (dx / dist) * f;
        const fy = (dy / dist) * f;
        const fz = (dz / dist) * f;

        if (e.source !== draggedNode) {{
          e.source.vx += fx;
          e.source.vy += fy;
          if (viewMode === '3D') e.source.vz += fz;
        }}
        if (e.target !== draggedNode) {{
          e.target.vx -= fx;
          e.target.vy -= fy;
          if (viewMode === '3D') e.target.vz -= fz;
        }}
      }}

      // 3. 阻尼衰减
      const damping = 0.72;
      for (const n of nodes) {{
        if (n === draggedNode) continue;
        n.vx *= damping;
        n.vy *= damping;
        n.vz *= damping;
        n.x += n.vx;
        n.y += n.vy;
        n.z += n.vz;
      }}

      alpha *= 0.985;
    }}

    // ==================== 3D 旋转透视投影变换 ====================
    function project3D(x, y, z) {{
      // 欧拉角旋转：绕 Y 轴偏航，绕 X 轴俯仰
      const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
      const x1 = x * cosY - z * sinY;
      const z1 = z * cosY + x * sinY;

      const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
      const y2 = y * cosX - z1 * sinX;
      const z2 = z1 * cosX + y * sinX;

      // 透视景深投影
      const distance = cameraZ + z2;
      const fov = 650;
      const scale = fov / Math.max(80, distance);

      return {{
        screenX: width / 2 + pan3D.x + x1 * scale,
        screenY: height / 2 + pan3D.y + y2 * scale,
        scale: scale,
        zDepth: z2
      }};
    }}

    // ==================== 渲染主引擎 ====================
    let filterText = "";
    document.getElementById('searchInput').addEventListener('input', (e) => {{
      filterText = e.target.value.toLowerCase().trim();
      reheatPhysics(0.3);
    }});

    function render() {{
      ctx.clearRect(0, 0, width, height);

      // 计算每个节点在当前视图模式下的投影坐标
      if (viewMode === '3D') {{
        for (const n of nodes) {{
          const proj = project3D(n.x, n.y, n.z);
          n.projX = proj.screenX;
          n.projY = proj.screenY;
          n.projScale = proj.scale;
          n.projZ = proj.zDepth;
        }}
        // 按 3D 景深 zDepth 从远到近排序渲染
        nodes.sort((a, b) => a.projZ - b.projZ);
      }} else {{
        for (const n of nodes) {{
          n.projX = transform2D.x + n.x * transform2D.k;
          n.projY = transform2D.y + n.y * transform2D.k;
          n.projScale = transform2D.k;
          n.projZ = 0;
        }}
      }}

      const hasFocusChain = activeCallChainNodes.size > 0 || activePathChainNodes.size > 0;
      const activeNeighbors = hoveredNode ? allAdjMap.get(hoveredNode.id) : null;

      // 1. 绘制边
      for (const e of visibleEdges) {{
        let isPathEdge = activePathChainEdges.has(`${{e.source.id}}->${{e.target.id}}`);
        let isChainEdge = isPathEdge || activeCallChainEdges.has(`${{e.source.id}}->${{e.target.id}}`);
        let isHoverEdge = hoveredNode && (e.source === hoveredNode || e.target === hoveredNode);
        let isMatchEdge = filterText && (e.source.name.toLowerCase().includes(filterText) || e.target.name.toLowerCase().includes(filterText));

        ctx.beginPath();
        ctx.moveTo(e.source.projX, e.source.projY);
        ctx.lineTo(e.target.projX, e.target.projY);

        if (isChainEdge) {{
          // 多跳调用延伸光束：明亮琥珀金流动光效
          ctx.strokeStyle = '#f59e0b';
          ctx.lineWidth = 2.8 * (viewMode === '3D' ? e.source.projScale : 1);
          ctx.globalAlpha = 1.0;
        }} else if (isHoverEdge || isMatchEdge) {{
          ctx.strokeStyle = '#38bdf8';
          ctx.lineWidth = 2.0 * (viewMode === '3D' ? e.source.projScale : 1);
          ctx.globalAlpha = 0.95;
        }} else if (hasFocusChain || hoveredNode || filterText) {{
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
          ctx.lineWidth = 0.5;
          ctx.globalAlpha = 0.15;
        }} else {{
          // 默认根据关系类型区分颜色
          if (e.kind === 'calls') {{
            ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)'; // 调用链路为高亮淡蓝
          }} else if (e.kind === 'imports') {{
            ctx.strokeStyle = 'rgba(168, 85, 247, 0.18)'; // 导入依赖为紫色
          }} else {{
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
          }}
          ctx.lineWidth = 0.8 * (viewMode === '3D' ? e.source.projScale : 1);
          ctx.globalAlpha = 0.6;
        }}
        ctx.stroke();

        // 为深层调用链路画箭头延伸指示
        if (isChainEdge || (isHoverEdge && e.kind === 'calls')) {{
          drawArrow(ctx, e.source.projX, e.source.projY, e.target.projX, e.target.projY, 8);
        }}
      }}
      ctx.globalAlpha = 1.0;

      // 2. 绘制节点
      for (const n of nodes) {{
        let isSelected = (n === selectedNode);
        let isHovered = (n === hoveredNode);
        let inPath = activePathChainNodes.has(n.id);
        let inChain = inPath || activeCallChainNodes.has(n.id);
        let isNeighbor = activeNeighbors ? activeNeighbors.has(n.id) : false;
        let isMatched = filterText ? (n.name.toLowerCase().includes(filterText) || n.path.toLowerCase().includes(filterText)) : false;

        let isDimmed = (hasFocusChain && !inChain) || 
                       (hoveredNode && !isHovered && !isNeighbor) || 
                       (filterText && !isMatched);

        const r = Math.max(3, n.radius * n.projScale);

        ctx.beginPath();
        ctx.arc(n.projX, n.projY, r, 0, 2 * Math.PI);

        if (inChain || isSelected) {{
          ctx.fillStyle = '#f59e0b'; // 延伸链条上的节点赋予高亮琥珀金
          ctx.shadowColor = '#f59e0b';
          ctx.shadowBlur = 14;
        }} else if (isHovered || isMatched) {{
          ctx.fillStyle = '#38bdf8';
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = 12;
        }} else if (isNeighbor) {{
          ctx.fillStyle = '#a78bfa';
          ctx.shadowColor = '#a78bfa';
          ctx.shadowBlur = 8;
        }} else {{
          ctx.fillStyle = n.color;
          ctx.shadowBlur = 0;
        }}

        ctx.globalAlpha = isDimmed ? 0.15 : 1.0;
        ctx.fill();

        // 边框立体反光
        ctx.strokeStyle = (inChain || isHovered || isMatched) ? '#ffffff' : 'rgba(255,255,255,0.25)';
        ctx.lineWidth = (inChain || isHovered) ? 2.2 : 0.8;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // 标签文字显示
        const showLabel = inChain || isHovered || isSelected || isNeighbor || isMatched || (n.deg >= 12 && n.projScale > 0.8);
        if (showLabel && !isDimmed) {{
          ctx.font = `${{Math.max(10, Math.min(13, 11 * n.projScale))}}px sans-serif`;
          ctx.fillStyle = (inChain || isHovered) ? '#f59e0b' : '#f1f5f9';
          ctx.fillText(n.name, n.projX + r + 4, n.projY + 3);
        }}
      }}
      ctx.globalAlpha = 1.0;
    }}

    function drawArrow(context, fromx, fromy, tox, toy, headlen) {{
      const dx = tox - fromx;
      const dy = toy - fromy;
      const angle = Math.atan2(dy, dx);
      const midX = (fromx + tox) / 2;
      const midY = (fromy + toy) / 2;

      context.beginPath();
      context.moveTo(midX, midY);
      context.lineTo(midX - headlen * Math.cos(angle - Math.PI / 6), midY - headlen * Math.sin(angle - Math.PI / 6));
      context.moveTo(midX, midY);
      context.lineTo(midX - headlen * Math.cos(angle + Math.PI / 6), midY - headlen * Math.sin(angle + Math.PI / 6));
      context.stroke();
    }}

    function tick() {{
      if (physicsRunning) {{
        stepPhysics();
      }}
      render();
      if (physicsRunning || isMouseDown || alpha > 0.005) {{
        requestAnimationFrame(tick);
      }}
    }}
    requestAnimationFrame(tick);

    // ==================== 鼠标拾取与 3D/2D 交互事件 ====================
    function getNodeAtScreen(sx, sy) {{
      for (let i = nodes.length - 1; i >= 0; i--) {{
        const n = nodes[i];
        const r = Math.max(4, n.radius * n.projScale);
        const dx = n.projX - sx;
        const dy = n.projY - sy;
        if (dx * dx + dy * dy <= (r + 4) * (r + 4)) {{
          return n;
        }}
      }}
      return null;
    }}

    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    canvas.addEventListener('mousedown', (e) => {{
      isMouseDown = true;
      mouseButton = e.button;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      const rect = canvas.getBoundingClientRect();
      const hit = getNodeAtScreen(e.clientX - rect.left, e.clientY - rect.top);

      if (hit && e.button === 0) {{
        draggedNode = hit;
        reheatPhysics(0.7);
      }}
    }});

    window.addEventListener('mousemove', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;

      if (isMouseDown) {{
        const dx = e.clientX - lastMouseX;
        const dy = e.clientY - lastMouseY;
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;

        if (draggedNode) {{
          // 拖动节点
          if (viewMode === '2D') {{
            draggedNode.x += dx / transform2D.k;
            draggedNode.y += dy / transform2D.k;
          }} else {{
            // 3D 模式下将屏幕拖动映射到摄像机平面
            draggedNode.x += dx / draggedNode.projScale;
            draggedNode.y += dy / draggedNode.projScale;
          }}
          draggedNode.vx = 0;
          draggedNode.vy = 0;
          reheatPhysics(0.3);
        }} else if (viewMode === '3D') {{
          if (mouseButton === 0) {{
            // 左键拖拽空白：3D 欧拉旋转 (围绕球心 360 度任意旋转)
            rotY += dx * 0.007;
            rotX += dy * 0.007;
          }} else {{
            // 右键拖拽：3D 画布平移
            pan3D.x += dx;
            pan3D.y += dy;
          }}
        }} else {{
          // 2D 画布平移
          transform2D.x += dx;
          transform2D.y += dy;
        }}
      }} else {{
        // 悬停检测
        const hit = getNodeAtScreen(sx, sy);
        if (hit !== hoveredNode) {{
          hoveredNode = hit;
          if (hit) {{
            tooltip.style.display = 'block';
            tooltip.style.left = (e.clientX + 14) + 'px';
            tooltip.style.top = (e.clientY + 14) + 'px';
            const targets = outgoingCallsMap.get(hit.id) || [];
            tooltip.innerHTML = `
              <div style="font-weight:600; color:#38bdf8; font-size:0.84rem;">${{hit.name}}</div>
              <div style="color:#94a3b8; font-size:0.72rem; margin-top:2px;">类型: <strong>${{hit.kind}}</strong> | 社区: #${{hit.comm}}</div>
              <div style="color:#64748b; font-size:0.7rem; margin-top:2px; word-break:break-all;">${{hit.path}}:${{hit.line}}</div>
              <div style="color:#34d399; font-size:0.72rem; margin-top:2px;">度数: ${{hit.deg}} (直接调用下游: ${{targets.length}} 个组件)</div>
              ${{hit.doc ? `<div style="color:#cbd5e1; font-size:0.7rem; margin-top:4px; border-top:1px dashed rgba(255,255,255,0.1); padding-top:3px;">${{hit.doc}}</div>` : ''}}
              <div style="color:#f59e0b; font-size:0.68rem; margin-top:4px;">💡 单击该节点可展开追踪其纵向多级调用链路延伸</div>
            `;
          }} else {{
            tooltip.style.display = 'none';
          }}
        }} else if (hoveredNode) {{
          tooltip.style.left = (e.clientX + 14) + 'px';
          tooltip.style.top = (e.clientY + 14) + 'px';
        }}
      }}
    }});

    window.addEventListener('mouseup', () => {{
      isMouseDown = false;
      draggedNode = null;
    }});

    // 滚轮缩放
    canvas.addEventListener('wheel', (e) => {{
      e.preventDefault();
      if (viewMode === '3D') {{
        // 3D 摄像机沿景深前后推进推远
        cameraZ = Math.min(2200, Math.max(180, cameraZ + e.deltaY * 0.9));
      }} else {{
        const rect = canvas.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;
        const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
        const newScale = Math.min(6.0, Math.max(0.1, transform2D.k * zoomFactor));

        const mouseWorldX = (sx - transform2D.x) / transform2D.k;
        const mouseWorldY = (sy - transform2D.y) / transform2D.k;

        transform2D.k = newScale;
        transform2D.x = sx - mouseWorldX * transform2D.k;
        transform2D.y = sy - mouseWorldY * transform2D.k;
      }}
    }}, {{ passive: false }});

    // 点击节点：触发多级纵向调用链延伸追踪
    canvas.addEventListener('click', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const hit = getNodeAtScreen(sx, sy);

      if (hit) {{
        selectedNode = hit;
        const chain = traceCallChain(hit.id);

        const det = document.getElementById('nodeDetails');
        det.style.display = 'block';
        document.getElementById('detName').innerText = hit.name;
        document.getElementById('detKind').innerText = `类型: ${{hit.kind}} (社区 #${{hit.comm}})`;
        document.getElementById('detPath').innerText = `${{hit.path}}:${{hit.line}}`;
        document.getElementById('detDeg').innerText = `度数: ${{hit.deg}} (入度: ${{hit.in_deg}}, 出度: ${{hit.out_deg}})`;

        const chainContainer = document.getElementById('downstreamChainList');
        if (chain.length > 0) {{
          chainContainer.innerHTML = chain.map(c => `
            <div class="chain-node" onclick="selectNodeById('${{c.targetId}}')" title="点击跳转聚焦">
              <span style="color:#f59e0b; font-weight:bold;">+${{c.depth}}跳:</span> ${{c.pathText}}
            </div>
          `).join('');
        }} else {{
          chainContainer.innerHTML = `<span style="color:#64748b; font-size:0.7rem;">未发现直接下游调用延伸 (已到叶子节点)</span>`;
        }}

        reheatPhysics(0.3);
      }}
    }});

    function selectNodeById(nid) {{
      const node = nodeMap.get(nid);
      if (node) {{
        selectedNode = node;
        traceCallChain(node.id);
        focusNode(node);
      }}
    }}

    function clearSelection() {{
      selectedNode = null;
      activeCallChainNodes.clear();
      activeCallChainEdges.clear();
      document.getElementById('nodeDetails').style.display = 'none';
      reheatPhysics(0.2);
    }}

    // ==================== HUD 视角控制 ====================
    function zoomIn() {{
      if (viewMode === '3D') cameraZ = Math.max(180, cameraZ - 120);
      else transform2D.k = Math.min(6.0, transform2D.k * 1.25);
    }}
    function zoomOut() {{
      if (viewMode === '3D') cameraZ = Math.min(2200, cameraZ + 120);
      else transform2D.k = Math.max(0.1, transform2D.k * 0.8);
    }}
    function resetView() {{
      if (viewMode === '3D') {{
        rotX = 0.25; rotY = -0.4;
        cameraZ = 750;
        pan3D = {{ x: 0, y: 0 }};
      }} else {{
        transform2D.k = 1.0;
        transform2D.x = width / 2;
        transform2D.y = height / 2;
      }}
      clearSelection();
      reheatPhysics(0.4);
    }}
    function togglePhysics() {{
      physicsRunning = !physicsRunning;
      document.getElementById('physicsToggleBtn').innerText = physicsRunning ? '⏸️ 暂停运动' : '▶️ 恢复运动';
      if (physicsRunning) {{
        reheatPhysics(0.5);
      }}
    }}
    function focusCommunity(commId) {{
      const commNodes = nodes.filter(n => n.comm === commId);
      if (!commNodes.length) return;
      let avgX = 0, avgY = 0, avgZ = 0;
      for (const n of commNodes) {{
        avgX += n.x; avgY += n.y; avgZ += n.z;
      }}
      avgX /= commNodes.length;
      avgY /= commNodes.length;
      avgZ /= commNodes.length;

      if (viewMode === '3D') {{
        pan3D.x = -avgX * 0.8;
        pan3D.y = -avgY * 0.8;
        cameraZ = 550;
      }} else {{
        transform2D.k = 1.6;
        transform2D.x = width / 2 - avgX * transform2D.k;
        transform2D.y = height / 2 - avgY * transform2D.k;
      }}
      reheatPhysics(0.4);
    }}
    function focusNode(node) {{
      if (viewMode === '3D') {{
        pan3D.x = -node.x * 0.9;
        pan3D.y = -node.y * 0.9;
        cameraZ = 450;
      }} else {{
        transform2D.k = 1.8;
        transform2D.x = width / 2 - node.x * transform2D.k;
        transform2D.y = height / 2 - node.y * transform2D.k;
      }}
      reheatPhysics(0.3);
    }}
  </script>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
