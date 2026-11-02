"""
Graph-RAG 核心数据模型 (Data Models)
忠实对齐 Graph-RAG 规范：
- 节点 (Node): 代码实体 (File, Class, Function, SQL Table, Doc Section)
- 边 (Edge): 实体间关联 (Defines, Calls, Imports, Inherits, ForeignKey, Explains)
- 置信度体系 (Confidence Tagging):
    - EXTRACTED (1.0): 确定性 AST 提取
    - INFERRED (0.55 ~ 0.95): 二阶段符号推断与上下文对齐
    - AMBIGUOUS (0.5): 存在歧义或不确定调用，标记人工核对
- 图拓扑结构与报告
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class ConfidenceLevel(str, Enum):
    """边置信度分级"""
    EXTRACTED = "EXTRACTED"   # 1.0: 纯确定性 AST/语法树显式提取
    INFERRED = "INFERRED"     # 0.55 ~ 0.95: 符号推导/上下文关联
    AMBIGUOUS = "AMBIGUOUS"   # 0.5: 存在多义性/动态调用，需警示


class NodeKind(str, Enum):
    """节点类型"""
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    SQL_TABLE = "sql_table"
    SQL_COLUMN = "sql_column"
    DOC_SECTION = "doc_section"
    CONFIG = "config"


class EdgeKind(str, Enum):
    """关系类型"""
    DEFINES = "defines"             # 包含/定义（如 文件定义类、类定义方法）
    IMPORTS = "imports"             # 导入依赖
    CALLS = "calls"                 # 函数/方法调用
    INHERITS = "inherits"           # 类继承
    REFERENCES = "references"       # 变量/常量/配置引用
    FOREIGN_KEY = "foreign_key"     # SQL 外键关联
    EXPLAINS = "explains"           # 文档与代码的说明关系
    SIMILAR_TO = "similar_to"       # 语义/行为相近


@dataclass
class Node:
    """图节点"""
    id: str                         # 全局唯一标识符 (如 "app.services.data_engine:load_data")
    name: str                       # 简短名称 (如 "load_data")
    kind: NodeKind                  # 类型
    path: str                       # 相对文件路径
    line: int = 1                   # 声明起始行
    end_line: int = 1               # 声明结束行
    docstring: Optional[str] = None # 文档注释 / 摘要
    community_id: int = -1          # Leiden / Louvain 划分的社群社区 ID
    degree: int = 0                 # 节点度数 (入度+出度)
    in_degree: int = 0              # 入度 (被调用/被依赖数)
    out_degree: int = 0             # 出度 (调用/依赖外部数)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value if isinstance(self.kind, NodeKind) else str(self.kind)
        return d


@dataclass
class Edge:
    """图边 (关系)"""
    source: str                     # 源节点 ID
    target: str                     # 目标节点 ID
    kind: EdgeKind                  # 关系类型
    confidence: ConfidenceLevel     # 置信度 (EXTRACTED, INFERRED, AMBIGUOUS)
    confidence_score: float = 1.0   # 置信度具体分值 (0.0 ~ 1.0)
    weight: float = 1.0             # 边权重 (用于图社区密度计算)
    explanation: Optional[str] = None # 对该条边的解析说明
    line: int = 0                   # 发生关系的行号 (若有)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value if isinstance(self.kind, EdgeKind) else str(self.kind)
        d["confidence"] = self.confidence.value if isinstance(self.confidence, ConfidenceLevel) else str(self.confidence)
        return d


@dataclass
class CommunityInfo:
    """社群聚类信息"""
    community_id: int
    name: str                       # 自动归纳的社区命名 (如 "Data Processing Subsystem")
    size: int
    nodes: List[str]                # 包含的节点 ID
    central_nodes: List[str]        # 社区内部中心节点 (God Nodes of community)
    internal_density: float         # 内部边密度
    description: str = ""


@dataclass
class TopologyInsight:
    """拓扑深度分析见解"""
    god_nodes: List[Dict[str, Any]]                # 核心中枢节点 (最高度数中心性)
    surprising_connections: List[Dict[str, Any]]   # 意外跨界连接 (跨不同社区的隐蔽长边)
    cycles: List[List[str]]                        # 循环依赖环路
    orphan_nodes: List[Dict[str, Any]]             # 孤立/未被引用节点 (代码死角)
    total_nodes: int = 0
    total_edges: int = 0
    modularity: float = 0.0                        # 图划分模块度评分
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
