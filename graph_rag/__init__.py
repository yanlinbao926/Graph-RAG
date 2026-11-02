"""
Graph-RAG 核心引擎 (Graph-RAG Core Engine)
忠实对齐 Graph-RAG 原理与规范：
- 本地确定性 AST 提取 (Pass 1)
- 零向量数据库 (No Vector Store) / 零外部 Embedding 依赖
- 置信度三级分级体系 (EXTRACTED / INFERRED / AMBIGUOUS)
- 图模块度社群聚类 (Leiden / Louvain Modularity)
- 拓扑深度分析 (God Nodes, Surprising Connections, Cycles, Orphans)
- 多模态输出 (graph.json, GRAPH_REPORT.md, graph.mermaid, graph.html)
"""

from typing import Optional, Dict, Any, Tuple, List
from .models import (
    Node,
    Edge,
    ConfidenceLevel,
    NodeKind,
    EdgeKind,
    CommunityInfo,
    TopologyInsight
)
from .graph_builder import Graph, GraphBuilder
from .cluster import GraphClusterer
from .analyzer import GraphAnalyzer
from .exporter import GraphExporter


def scan_codebase(
    root_dir: str = ".",
    output_dir: Optional[str] = None
) -> Tuple[Graph, List[CommunityInfo], TopologyInsight, Optional[Dict[str, str]]]:
    """
    一键扫描代码库并生成确定性知识图谱与报告

    参数:
        root_dir: 待分析的代码库根目录 (默认当前目录)
        output_dir: 结果导出目录 (如指定，将输出 graph.json, GRAPH_REPORT.md 等)

    返回:
        (graph, communities, insights, exported_paths)
    """
    # 1. 静态 AST 提取与二阶段符号图构建
    builder = GraphBuilder(root_dir)
    graph = builder.build_graph()

    # 2. 社群聚类 (Leiden / Modularity 社区发现)
    clusterer = GraphClusterer(graph)
    communities = clusterer.detect_communities()

    # 3. 拓扑诊断分析 (God Nodes, Surprising Connections, Cycles)
    analyzer = GraphAnalyzer(graph)
    insights = analyzer.analyze()

    # 4. 导出交付物
    exported_paths = None
    if output_dir:
        exporter = GraphExporter(graph, communities, insights)
        exported_paths = exporter.export_all(output_dir)

    return graph, communities, insights, exported_paths


__all__ = [
    "scan_codebase",
    "Graph",
    "GraphBuilder",
    "GraphClusterer",
    "GraphAnalyzer",
    "GraphExporter",
    "Node",
    "Edge",
    "ConfidenceLevel",
    "NodeKind",
    "EdgeKind",
    "CommunityInfo",
    "TopologyInsight"
]
