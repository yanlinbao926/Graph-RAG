"""
Graph-RAG 图社群聚类引擎 (Community Detection & Clustering)
核心原则：
- 无需向量数据库 (No Vector Store)，无需外部 Embedding
- 图本身的拓扑连接密度 (Edge Density) 天然就是最强大的架构与语义聚类信号
- 兼容 NetworkX Louvain / Greedy Modularity，并提供内置轻量纯 Python 聚类保底
- 自动提取社区内部核心节点并智能命名子系统
"""

import collections
from typing import Dict, List, Set, Tuple
from .models import Node, Edge, CommunityInfo
from .graph_builder import Graph


class GraphClusterer:
    """图社群划分与凝聚度计算"""

    def __init__(self, graph: Graph):
        self.graph = graph

    def detect_communities(self) -> List[CommunityInfo]:
        """
        主聚类方法：
        优先使用 NetworkX 的 Louvain 算法，若不可用则使用自包含模块度优化聚类
        """
        partition: Dict[str, int] = {}

        # 尝试使用 NetworkX
        nx_graph = self.graph.to_networkx()
        if nx_graph is not None and len(nx_graph) > 0:
            try:
                import networkx as nx
                from networkx.algorithms import community as nx_comm
                # 转换为无向图进行社区划分
                undirected_G = nx_graph.to_undirected()
                if hasattr(nx_comm, "louvain_communities"):
                    comms = nx_comm.louvain_communities(undirected_G, weight="weight", seed=42)
                else:
                    comms = list(nx_comm.greedy_modularity_communities(undirected_G, weight="weight"))

                for comm_id, node_set in enumerate(comms):
                    for nid in node_set:
                        if nid in self.graph.nodes:
                            partition[nid] = comm_id
            except Exception:
                partition = self._builtin_label_propagation()
        else:
            partition = self._builtin_label_propagation()

        # 将每个节点的 community_id 写回 Node
        community_buckets: Dict[int, List[str]] = collections.defaultdict(list)
        for nid, comm_id in partition.items():
            if nid in self.graph.nodes:
                self.graph.nodes[nid].community_id = comm_id
                community_buckets[comm_id].append(nid)

        # 为未分配的孤立节点分配独立社区
        next_cid = max(community_buckets.keys(), default=-1) + 1
        for nid, node in self.graph.nodes.items():
            if node.community_id == -1:
                node.community_id = next_cid
                community_buckets[next_cid].append(nid)
                next_cid += 1

        # 构建 CommunityInfo 列表并进行特征提取
        communities_result: List[CommunityInfo] = []
        for comm_id, nodes in community_buckets.items():
            if not nodes:
                continue
            # 计算社区内中心节点 (按内部与总体度数排序)
            sorted_nodes = sorted(nodes, key=lambda x: self.graph.nodes[x].degree, reverse=True)
            central_nodes = sorted_nodes[:3]

            # 智能推断子系统命名
            comm_name = self._infer_community_name(nodes, central_nodes, comm_id)

            # 计算内部边密度
            internal_edges = 0
            node_set = set(nodes)
            for nid in nodes:
                for target in self.graph.neighbors(nid):
                    if target in node_set:
                        internal_edges += 1

            n_count = len(nodes)
            max_possible_edges = n_count * (n_count - 1) if n_count > 1 else 1
            density = round(internal_edges / max(1, max_possible_edges), 3)

            communities_result.append(CommunityInfo(
                community_id=comm_id,
                name=comm_name,
                size=len(nodes),
                nodes=nodes,
                central_nodes=central_nodes,
                internal_density=density,
                description=f"Subsystem cluster containing {len(nodes)} components, led by {', '.join(central_nodes[:2])}"
            ))

        # 按规模由大到小排序
        communities_result.sort(key=lambda c: c.size, reverse=True)
        return communities_result

    def _builtin_label_propagation(self) -> Dict[str, int]:
        """纯 Python 自包含标签传播聚类算法 (保底备用)"""
        labels: Dict[str, int] = {}
        # 初始时每个节点属于以自身索引为标签的社区
        for idx, nid in enumerate(self.graph.nodes.keys()):
            labels[nid] = idx

        # 迭代收敛
        changed = True
        iterations = 0
        max_iter = 15

        while changed and iterations < max_iter:
            changed = False
            iterations += 1
            for nid in list(self.graph.nodes.keys()):
                neighbors = set(self.graph.neighbors(nid)) | set(self.graph.predecessors(nid))
                if not neighbors:
                    continue
                # 统计邻居标签频率
                freq = collections.Counter(labels.get(nbr, -1) for nbr in neighbors if nbr in labels)
                if not freq:
                    continue
                most_common_label = freq.most_common(1)[0][0]
                if labels[nid] != most_common_label:
                    labels[nid] = most_common_label
                    changed = True

        # 压缩社区 ID 为 0, 1, 2...
        unique_labels = sorted(list(set(labels.values())))
        label_map = {lbl: new_id for new_id, lbl in enumerate(unique_labels)}
        return {nid: label_map[lbl] for nid, lbl in labels.items()}

    def _infer_community_name(self, nodes: List[str], central_nodes: List[str], comm_id: int) -> str:
        """根据节点路径与核心节点名称，智能生成架构子系统名称"""
        path_tokens = []
        for nid in nodes:
            node = self.graph.nodes.get(nid)
            if node and node.path and not node.path.startswith("<"):
                parts = node.path.replace("\\", "/").split("/")
                if len(parts) > 1:
                    path_tokens.append(parts[0]) # 顶级目录如 app
                    if len(parts) > 2:
                        path_tokens.append(parts[1]) # 二级目录如 services, agent

        if path_tokens:
            most_freq = collections.Counter(path_tokens).most_common(1)[0][0]
            label = most_freq.capitalize()
            if central_nodes:
                lead_name = self.graph.nodes[central_nodes[0]].name
                return f"{label} Subsystem ({lead_name})"
            return f"{label} Cluster #{comm_id}"

        if central_nodes:
            lead_name = self.graph.nodes[central_nodes[0]].name
            return f"Cluster #{comm_id} ({lead_name})"

        return f"Component Group #{comm_id}"
