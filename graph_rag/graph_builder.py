"""
Graph-RAG 图构建与二阶段符号解析引擎 (Graph Builder & Symbol Resolution)
核心机制：
1. Pass 1 扫描全局节点与符号，建立全局符号索引 (Symbol Table)
2. Pass 2 二阶段消歧义与置信度标定 (Symbol Resolution & Confidence Tagging):
   - 本地作用域命中 -> EXTRACTED (1.0)
   - 精确 Import 解析 -> INFERRED (0.95)
   - 跨文件唯一同名方法推断 -> INFERRED (0.75)
   - 多重歧义方法候选 -> AMBIGUOUS (0.50)
3. 外部第三方库依赖收敛与悬空节点规范化
"""

import os
from typing import Dict, List, Set, Tuple, Optional, Any
from .models import Node, Edge, NodeKind, EdgeKind, ConfidenceLevel
from .extractor import PythonASTExtractor, SQLExtractor, MarkdownExtractor, SymbolRecord


class Graph:
    """
    轻量自包含图数据结构
    与 NetworkX API 完全双向兼容，同时即使在无第三方图库环境下亦能独立运行
    """
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adj: Dict[str, Dict[str, Edge]] = {}      # source -> {target: Edge}
        self._rev_adj: Dict[str, Dict[str, Edge]] = {}  # target -> {source: Edge}

    def add_node(self, node: Node):
        self.nodes[node.id] = node
        if node.id not in self._adj:
            self._adj[node.id] = {}
        if node.id not in self._rev_adj:
            self._rev_adj[node.id] = {}

    def add_edge(self, edge: Edge):
        self.edges.append(edge)
        if edge.source not in self._adj:
            self._adj[edge.source] = {}
        if edge.target not in self._rev_adj:
            self._rev_adj[edge.target] = {}
        self._adj[edge.source][edge.target] = edge
        self._rev_adj[edge.target][edge.source] = edge

    def neighbors(self, node_id: str) -> List[str]:
        return list(self._adj.get(node_id, {}).keys())

    def predecessors(self, node_id: str) -> List[str]:
        return list(self._rev_adj.get(node_id, {}).keys())

    def update_degrees(self):
        """更新每个节点的出度、入度与综合度数"""
        for nid, node in self.nodes.items():
            out_deg = len(self._adj.get(nid, {}))
            in_deg = len(self._rev_adj.get(nid, {}))
            node.out_degree = out_deg
            node.in_degree = in_deg
            node.degree = in_deg + out_deg

    def to_networkx(self):
        """若环境中有 networkx，一键导出为 nx.DiGraph"""
        try:
            import networkx as nx
            G = nx.DiGraph()
            for nid, node in self.nodes.items():
                G.add_node(nid, **node.to_dict())
            for edge in self.edges:
                G.add_edge(edge.source, edge.target, **edge.to_dict())
            return G
        except ImportError:
            return None


class GraphBuilder:
    """代码库到确定性知识图谱构建器"""

    IGNORE_DIRS = {
        ".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".mypy_cache",
        "venv", ".venv", "env", "node_modules", "dist", "build", ".idea", ".vscode"
    }

    IGNORE_EXTENSIONS = {
        ".pyc", ".pyo", ".pyd", ".png", ".jpg", ".jpeg", ".gif", ".ico",
        ".svg", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".tar", ".gz"
    }

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.py_extractor = PythonASTExtractor(self.root_dir)
        self.sql_extractor = SQLExtractor()
        self.doc_extractor = MarkdownExtractor()

        # 全局符号索引表
        self.symbol_table: Dict[str, List[SymbolRecord]] = {} # name -> [records]
        self.module_nodes: Dict[str, str] = {}                 # mod_path -> node_id

    def build_graph(self) -> Graph:
        """主构建入口：扫描全库并执行两阶段构图"""
        graph = Graph()
        all_raw_calls: List[Dict[str, Any]] = []

        # ----------------------------------------------------
        # Pass 1: 遍历文件，确定性 AST 提取与符号注册
        # ----------------------------------------------------
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]

            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.IGNORE_EXTENSIONS:
                    continue

                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, self.root_dir).replace("\\", "/")

                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue

                if ext == ".py":
                    nodes, edges, symbols, raw_calls = self.py_extractor.extract_file(rel_path, content)
                    for n in nodes:
                        graph.add_node(n)
                    for e in edges:
                        graph.add_edge(e)
                    for s in symbols:
                        self.symbol_table.setdefault(s.name, []).append(s)
                    all_raw_calls.extend(raw_calls)

                elif ext == ".sql":
                    nodes, edges = self.sql_extractor.extract_file(rel_path, content)
                    for n in nodes:
                        graph.add_node(n)
                    for e in edges:
                        graph.add_edge(e)

                elif ext in (".md", ".markdown"):
                    nodes, edges = self.doc_extractor.extract_file(rel_path, content)
                    for n in nodes:
                        graph.add_node(n)
                    for e in edges:
                        graph.add_edge(e)

        # ----------------------------------------------------
        # Pass 2: 二阶段符号调用消歧义与悬空边规范化
        # ----------------------------------------------------
        self._resolve_raw_calls(graph, all_raw_calls)
        self._normalize_external_and_symbol_edges(graph)

        # 更新度数
        graph.update_degrees()
        return graph

    def _resolve_raw_calls(self, graph: Graph, raw_calls: List[Dict[str, Any]]):
        """利用全局符号表消歧并生成精确的 Calls 边"""
        for item in raw_calls:
            caller_id = item["caller_id"]
            callee_name = item["callee_name"]
            call_type = item["type"]
            line = item.get("line", 0)
            local_imports = item.get("local_imports", {})

            # 1. 优先检查本地 import 映射 (如 from app.services.data_engine import load_data)
            if callee_name in local_imports:
                imported_target = local_imports[callee_name]
                matched_id = None
                for candidate in self.symbol_table.get(callee_name, []):
                    if imported_target in candidate.node_id or candidate.node_id.endswith(callee_name):
                        matched_id = candidate.node_id
                        break

                target_id = matched_id or f"symbol:{imported_target}"
                graph.add_edge(Edge(
                    source=caller_id,
                    target=target_id,
                    kind=EdgeKind.CALLS,
                    confidence=ConfidenceLevel.EXTRACTED,
                    confidence_score=1.0,
                    explanation=f"Calls imported symbol `{imported_target}`",
                    line=line
                ))
                continue

            # 2. 如果是对象方法调用 (obj.method)
            obj_name = item.get("object_name", "")
            if call_type == "attribute" and obj_name:
                candidates = self.symbol_table.get(callee_name, [])
                if len(candidates) == 1:
                    # 全局唯一匹配 -> INFERRED (0.85)
                    graph.add_edge(Edge(
                        source=caller_id,
                        target=candidates[0].node_id,
                        kind=EdgeKind.CALLS,
                        confidence=ConfidenceLevel.INFERRED,
                        confidence_score=0.85,
                        explanation=f"Method `{callee_name}` inferred to unique class implementation `{candidates[0].node_id}`",
                        line=line
                    ))
                elif len(candidates) > 1:
                    # 多重匹配候选 -> AMBIGUOUS (0.50)
                    for cand in candidates[:2]: # 关联最高可能的前2项
                        graph.add_edge(Edge(
                            source=caller_id,
                            target=cand.node_id,
                            kind=EdgeKind.CALLS,
                            confidence=ConfidenceLevel.AMBIGUOUS,
                            confidence_score=0.50,
                            explanation=f"Ambiguous method call `{obj_name}.{callee_name}`, multiple candidate implementations found",
                            line=line
                        ))
                continue

            # 3. 直接调用未导入函数 (检查全局是否唯一)
            candidates = self.symbol_table.get(callee_name, [])
            if len(candidates) == 1:
                graph.add_edge(Edge(
                    source=caller_id,
                    target=candidates[0].node_id,
                    kind=EdgeKind.CALLS,
                    confidence=ConfidenceLevel.INFERRED,
                    confidence_score=0.75,
                    explanation=f"Inferred direct call to global symbol `{candidates[0].node_id}`",
                    line=line
                ))

    def _normalize_external_and_symbol_edges(self, graph: Graph):
        """将未匹配的 symbol: 或 module: 规范化，确保图的节点完备与拓扑闭合"""
        missing_nodes: Dict[str, Node] = {}

        for edge in graph.edges:
            # 检查 target 是否已在 graph.nodes 中
            if edge.target not in graph.nodes and edge.target not in missing_nodes:
                if edge.target.startswith("module:"):
                    mod_name = edge.target[7:]
                    missing_nodes[edge.target] = Node(
                        id=edge.target,
                        name=mod_name,
                        kind=NodeKind.MODULE,
                        path="<external>",
                        docstring=f"External / Library Module `{mod_name}`",
                        metadata={"is_external": True}
                    )
                elif edge.target.startswith("symbol:"):
                    sym_name = edge.target[7:]
                    missing_nodes[edge.target] = Node(
                        id=edge.target,
                        name=sym_name,
                        kind=NodeKind.FUNCTION,
                        path="<symbol>",
                        docstring=f"Unresolved Symbol `{sym_name}`",
                        metadata={"is_unresolved": True}
                    )

        for nid, node in missing_nodes.items():
            graph.add_node(node)
