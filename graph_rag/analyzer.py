"""
Graph-RAG 图拓扑深度分析器 (Topology Analyzer)
忠实对齐 Graph-RAG 拓扑诊断核心特性：
1. God Nodes (核心中枢上帝节点): 度中心性分析，定位架构枢纽
2. Surprising Connections (意外跨界连接): 跨不同子系统社区的长边，暴露潜在耦合或桥接层
3. Import & Call Cycles (循环依赖检测): 识别静态调用拓扑环
4. Orphan Nodes (代码死角与未引用盲区)
5. 置信度审计分布 (Confidence Distribution)
"""

from typing import Dict, List, Set, Any
from .models import Node, Edge, TopologyInsight, ConfidenceLevel
from .graph_builder import Graph


class GraphAnalyzer:
    """拓扑指标与架构见解分析"""

    def __init__(self, graph: Graph):
        self.graph = graph

    def analyze(self) -> TopologyInsight:
        """运行全套拓扑诊断分析并返回洞察"""
        god_nodes = self._find_god_nodes(top_n=8)
        surprising_conns = self._find_surprising_connections(limit=15)
        cycles = self._detect_cycles(limit=10)
        orphans = self._find_orphan_nodes(limit=10)

        # 统计置信度分布
        conf_dist = {
            ConfidenceLevel.EXTRACTED.value: 0,
            ConfidenceLevel.INFERRED.value: 0,
            ConfidenceLevel.AMBIGUOUS.value: 0
        }
        for edge in self.graph.edges:
            c_val = edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence)
            conf_dist[c_val] = conf_dist.get(c_val, 0) + 1

        return TopologyInsight(
            god_nodes=god_nodes,
            surprising_connections=surprising_conns,
            cycles=cycles,
            orphan_nodes=orphans,
            total_nodes=len(self.graph.nodes),
            total_edges=len(self.graph.edges),
            confidence_distribution=conf_dist
        )

    def _find_god_nodes(self, top_n: int = 8) -> List[Dict[str, Any]]:
        """基于度中心性 (Degree Centrality) 计算最核心的 God Nodes"""
        sorted_nodes = sorted(
            self.graph.nodes.values(),
            key=lambda n: (n.degree, n.in_degree),
            reverse=True
        )

        gods = []
        for node in sorted_nodes[:top_n]:
            if node.path.startswith("<external>") or node.path.startswith("<symbol>"):
                continue # 排除外部库，聚焦本库代码
            gods.append({
                "id": node.id,
                "name": node.name,
                "kind": node.kind.value if hasattr(node.kind, "value") else str(node.kind),
                "path": node.path,
                "degree": node.degree,
                "in_degree": node.in_degree,
                "out_degree": node.out_degree,
                "community_id": node.community_id,
                "role": "Central Hub" if node.degree >= 5 else "Key Component"
            })
        return gods

    def _find_surprising_connections(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        找出跨越不同社区的跨界长边 (Surprising Connections)
        往往代表跨模块桥接层、中介层或隐藏的跨子系统耦合
        """
        surprising = []
        for edge in self.graph.edges:
            src = self.graph.nodes.get(edge.source)
            tgt = self.graph.nodes.get(edge.target)
            if not src or not tgt:
                continue

            # 跨社区并且双方不是外部占位
            if src.community_id != tgt.community_id and src.community_id != -1 and tgt.community_id != -1:
                surprising.append({
                    "source": edge.source,
                    "target": edge.target,
                    "source_name": src.name,
                    "target_name": tgt.name,
                    "source_community": src.community_id,
                    "target_community": tgt.community_id,
                    "kind": edge.kind.value if hasattr(edge.kind, "value") else str(edge.kind),
                    "confidence": edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence),
                    "explanation": edge.explanation or ""
                })

        # 按来源节点的度数重要性优先排序
        surprising.sort(key=lambda x: self.graph.nodes[x["source"]].degree if x["source"] in self.graph.nodes else 0, reverse=True)
        return surprising[:limit]

    def _detect_cycles(self, limit: int = 10) -> List[List[str]]:
        """检测调用和依赖拓扑中的循环环路 (Cycles)"""
        # 尝试使用 NetworkX
        nx_graph = self.graph.to_networkx()
        if nx_graph is not None:
            try:
                import networkx as nx
                raw_cycles = list(nx.simple_cycles(nx_graph))
                # 过滤只包含一个或两个节点的琐碎循环
                valid_cycles = [c for c in raw_cycles if len(c) >= 2]
                return valid_cycles[:limit]
            except Exception:
                pass

        # 内置 DFS 环检测
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Dict[str, int] = {}
        path: List[str] = []

        def dfs(u: str):
            if len(cycles) >= limit:
                return
            visited.add(u)
            rec_stack[u] = len(path)
            path.append(u)

            for v in self.graph.neighbors(u):
                if v not in visited:
                    dfs(v)
                elif v in rec_stack:
                    # 发现环路
                    cycle_start_idx = rec_stack[v]
                    cycle_path = path[cycle_start_idx:] + [v]
                    cycles.append(cycle_path)

            path.pop()
            del rec_stack[u]

        for nid in list(self.graph.nodes.keys()):
            if nid not in visited and len(cycles) < limit:
                dfs(nid)

        return cycles

    def _find_orphan_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """找出无引用节点 (入度为 0 且出度为 0，或者未被任何文件使用的潜在冗余代码)"""
        orphans = []
        for nid, node in self.graph.nodes.items():
            if node.path.startswith("<external>") or node.path.startswith("<symbol>"):
                continue
            if node.kind.value in ("file", "doc_section"):
                continue # 文件与文档本身不算孤儿
            if node.degree == 0 or (node.in_degree == 0 and node.out_degree == 0):
                orphans.append({
                    "id": node.id,
                    "name": node.name,
                    "kind": node.kind.value if hasattr(node.kind, "value") else str(node.kind),
                    "path": node.path,
                    "line": node.line
                })
        return orphans[:limit]
