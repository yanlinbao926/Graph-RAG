"""
Graph-RAG 静态代码与语义提取器 (Pass 1 Extractor)
遵循 Graph-RAG 确定性原则：
- 本地 AST 解析，0 API/Token 消耗
- 严格置信度标记：AST 显式结构 -> EXTRACTED (1.0)
- 提取 Module, Class, Function, Method, Import, Call, Inheritance, SQL Schema, Doc Section
"""

import ast
import os
import re
from typing import Dict, List, Tuple, Set, Optional, Any
from .models import Node, Edge, NodeKind, EdgeKind, ConfidenceLevel


class SymbolRecord:
    """内部符号记录，用于两阶段解析"""
    def __init__(self, name: str, node_id: str, kind: NodeKind, path: str, enclosing_class: Optional[str] = None):
        self.name = name
        self.node_id = node_id
        self.kind = kind
        self.path = path
        self.enclosing_class = enclosing_class


class PythonASTExtractor:
    """Python 代码确定性 AST 解析器"""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    def extract_file(self, rel_path: str, content: str) -> Tuple[List[Node], List[Edge], List[SymbolRecord], List[Dict[str, Any]]]:
        """
        解析单个 Python 文件
        返回: (nodes, edges, symbols, raw_calls)
        raw_calls 供第二阶段符号链接消歧
        """
        nodes: List[Node] = []
        edges: List[Edge] = []
        symbols: List[SymbolRecord] = []
        raw_calls: List[Dict[str, Any]] = []

        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError as e:
            # 语法错误文件仅作为普通文件节点记录
            file_node_id = f"file:{rel_path.replace(os.sep, '/')}"
            nodes.append(Node(
                id=file_node_id,
                name=os.path.basename(rel_path),
                kind=NodeKind.FILE,
                path=rel_path,
                docstring=f"SyntaxError during AST parse: {e}"
            ))
            return nodes, edges, symbols, raw_calls

        normalized_path = rel_path.replace("\\", "/")
        file_node_id = f"file:{normalized_path}"
        mod_name = os.path.splitext(normalized_path)[0].replace("/", ".")

        # 1. 创建文件节点
        file_doc = ast.get_docstring(tree)
        file_node = Node(
            id=file_node_id,
            name=os.path.basename(rel_path),
            kind=NodeKind.FILE,
            path=normalized_path,
            line=1,
            end_line=len(content.splitlines()),
            docstring=file_doc
        )
        nodes.append(file_node)

        # 记录局部导入表: {local_alias: target_module_or_name}
        local_imports: Dict[str, str] = {}

        # 遍历 AST 顶层与类内结构
        class ASTVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_scope_id = file_node_id
                self.current_class_name: Optional[str] = None
                self.current_func_id: Optional[str] = None

            def visit_Import(self, node: ast.Import):
                for alias in node.names:
                    imp_name = alias.name
                    as_name = alias.asname or imp_name
                    local_imports[as_name] = imp_name
                    
                    # 生成导入边
                    target_id = f"module:{imp_name}"
                    edges.append(Edge(
                        source=file_node_id,
                        target=target_id,
                        kind=EdgeKind.IMPORTS,
                        confidence=ConfidenceLevel.EXTRACTED,
                        confidence_score=1.0,
                        explanation=f"import {imp_name}",
                        line=node.lineno
                    ))
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom):
                from_mod = node.module or ""
                if node.level > 0:
                    # 相对导入解析
                    cur_parts = mod_name.split(".")[:-node.level]
                    if from_mod:
                        from_mod = ".".join(cur_parts + [from_mod])
                    else:
                        from_mod = ".".join(cur_parts)

                for alias in node.names:
                    full_target = f"{from_mod}.{alias.name}" if from_mod else alias.name
                    as_name = alias.asname or alias.name
                    local_imports[as_name] = full_target
                    
                    target_id = f"symbol:{full_target}"
                    edges.append(Edge(
                        source=file_node_id,
                        target=target_id,
                        kind=EdgeKind.IMPORTS,
                        confidence=ConfidenceLevel.EXTRACTED,
                        confidence_score=1.0,
                        explanation=f"from {from_mod} import {alias.name}",
                        line=node.lineno
                    ))
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef):
                class_node_id = f"{mod_name}:{node.name}"
                class_doc = ast.get_docstring(node)
                class_node = Node(
                    id=class_node_id,
                    name=node.name,
                    kind=NodeKind.CLASS,
                    path=normalized_path,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    docstring=class_doc
                )
                nodes.append(class_node)
                symbols.append(SymbolRecord(node.name, class_node_id, NodeKind.CLASS, normalized_path))

                # 文件 -> 类 的定义包含关系
                edges.append(Edge(
                    source=file_node_id,
                    target=class_node_id,
                    kind=EdgeKind.DEFINES,
                    confidence=ConfidenceLevel.EXTRACTED,
                    confidence_score=1.0,
                    explanation=f"Defines class {node.name}",
                    line=node.lineno
                ))

                # 类继承提取 (Inherits)
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = f"{getattr(base.value, 'id', '')}.{base.attr}"
                    if base_name:
                        edges.append(Edge(
                            source=class_node_id,
                            target=f"symbol:{base_name}",
                            kind=EdgeKind.INHERITS,
                            confidence=ConfidenceLevel.EXTRACTED,
                            confidence_score=1.0,
                            explanation=f"Inherits from {base_name}",
                            line=node.lineno
                        ))

                # 进入类作用域
                prev_class = self.current_class_name
                prev_scope = self.current_scope_id
                self.current_class_name = node.name
                self.current_scope_id = class_node_id

                self.generic_visit(node)

                self.current_class_name = prev_class
                self.current_scope_id = prev_scope

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._handle_func(node, is_async=False)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_func(node, is_async=True)

            def _handle_func(self, node: Any, is_async: bool):
                is_method = self.current_class_name is not None
                if is_method:
                    func_node_id = f"{mod_name}:{self.current_class_name}.{node.name}"
                    kind = NodeKind.METHOD
                else:
                    func_node_id = f"{mod_name}:{node.name}"
                    kind = NodeKind.FUNCTION

                func_doc = ast.get_docstring(node)
                func_node = Node(
                    id=func_node_id,
                    name=node.name,
                    kind=kind,
                    path=normalized_path,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    docstring=func_doc,
                    metadata={"is_async": is_async, "args": [a.arg for a in node.args.args]}
                )
                nodes.append(func_node)
                symbols.append(SymbolRecord(node.name, func_node_id, kind, normalized_path, self.current_class_name))

                # 父级 (File 或 Class) -> 函数的包含定义关系
                edges.append(Edge(
                    source=self.current_scope_id,
                    target=func_node_id,
                    kind=EdgeKind.DEFINES,
                    confidence=ConfidenceLevel.EXTRACTED,
                    confidence_score=1.0,
                    explanation=f"Defines {'method' if is_method else 'function'} {node.name}",
                    line=node.lineno
                ))

                prev_func = self.current_func_id
                prev_scope = self.current_scope_id
                self.current_func_id = func_node_id
                self.current_scope_id = func_node_id

                self.generic_visit(node)

                self.current_func_id = prev_func
                self.current_scope_id = prev_scope

            def visit_Call(self, node: ast.Call):
                caller_id = self.current_func_id or self.current_scope_id
                callee_name = ""

                if isinstance(node.func, ast.Name):
                    callee_name = node.func.id
                    raw_calls.append({
                        "caller_id": caller_id,
                        "callee_name": callee_name,
                        "line": node.lineno,
                        "type": "direct",
                        "local_imports": dict(local_imports)
                    })
                elif isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr
                    callee_name = attr_name
                    val_repr = ""
                    if isinstance(node.func.value, ast.Name):
                        val_repr = node.func.value.id
                    elif isinstance(node.func.value, ast.Attribute):
                        val_repr = f"{getattr(node.func.value.value, 'id', '')}.{node.func.value.attr}"
                    
                    raw_calls.append({
                        "caller_id": caller_id,
                        "callee_name": callee_name,
                        "object_name": val_repr,
                        "line": node.lineno,
                        "type": "attribute",
                        "local_imports": dict(local_imports)
                    })

                self.generic_visit(node)

        visitor = ASTVisitor()
        visitor.visit(tree)

        return nodes, edges, symbols, raw_calls


class SQLExtractor:
    """SQL 表模式与关系确定性提取器"""

    CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([`\"']?(\w+)[`\"']?)", re.IGNORECASE)
    FOREIGN_KEY_RE = re.compile(r"FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+([`\"']?(\w+)[`\"']?)\s*\(([^)]+)\)", re.IGNORECASE)
    JOIN_RE = re.compile(r"(?:LEFT|RIGHT|INNER|OUTER|CROSS)?\s*JOIN\s+([`\"']?(\w+)[`\"']?)\s+ON", re.IGNORECASE)

    def extract_file(self, rel_path: str, content: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []
        normalized_path = rel_path.replace("\\", "/")

        file_node_id = f"file:{normalized_path}"
        nodes.append(Node(
            id=file_node_id,
            name=os.path.basename(rel_path),
            kind=NodeKind.FILE,
            path=normalized_path,
            docstring="SQL Schema / Query File"
        ))

        # 查找所有建表语句
        tables_found: List[Tuple[str, int]] = []
        for match in self.CREATE_TABLE_RE.finditer(content):
            tbl_name = match.group(2)
            line = content[:match.start()].count("\n") + 1
            tbl_id = f"sql_table:{tbl_name}"
            nodes.append(Node(
                id=tbl_id,
                name=tbl_name,
                kind=NodeKind.SQL_TABLE,
                path=normalized_path,
                line=line,
                docstring=f"SQL Table definition `{tbl_name}`"
            ))
            edges.append(Edge(
                source=file_node_id,
                target=tbl_id,
                kind=EdgeKind.DEFINES,
                confidence=ConfidenceLevel.EXTRACTED,
                confidence_score=1.0,
                explanation=f"Defines table {tbl_name}",
                line=line
            ))
            tables_found.append((tbl_name, match.start()))

        # 查找外键约束 (Foreign Keys)
        for match in self.FOREIGN_KEY_RE.finditer(content):
            ref_table = match.group(2)
            line = content[:match.start()].count("\n") + 1
            # 找到所属的最近 table
            current_tbl = None
            for tbl_name, tbl_pos in reversed(tables_found):
                if tbl_pos < match.start():
                    current_tbl = tbl_name
                    break
            if current_tbl:
                edges.append(Edge(
                    source=f"sql_table:{current_tbl}",
                    target=f"sql_table:{ref_table}",
                    kind=EdgeKind.FOREIGN_KEY,
                    confidence=ConfidenceLevel.EXTRACTED,
                    confidence_score=1.0,
                    explanation=f"Foreign key reference to {ref_table}",
                    line=line
                ))

        return nodes, edges


class MarkdownExtractor:
    """Markdown 文档结构与知识关联提取器"""

    HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_REF_RE = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_\.]{2,})`")

    def extract_file(self, rel_path: str, content: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []
        normalized_path = rel_path.replace("\\", "/")

        file_node_id = f"file:{normalized_path}"
        nodes.append(Node(
            id=file_node_id,
            name=os.path.basename(rel_path),
            kind=NodeKind.FILE,
            path=normalized_path,
            docstring="Markdown Documentation"
        ))

        heading_stack: List[Tuple[int, str]] = [] # [(level, node_id)]

        for match in self.HEADING_RE.finditer(content):
            level = len(match.group(1))
            title = match.group(2).strip()
            line = content[:match.start()].count("\n") + 1
            sec_id = f"doc:{normalized_path}#{title.replace(' ', '-').lower()}"

            sec_node = Node(
                id=sec_id,
                name=title,
                kind=NodeKind.DOC_SECTION,
                path=normalized_path,
                line=line,
                docstring=f"Section: {title}"
            )
            nodes.append(sec_node)

            # 确定父级
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            parent_id = heading_stack[-1][1] if heading_stack else file_node_id
            edges.append(Edge(
                source=parent_id,
                target=sec_id,
                kind=EdgeKind.DEFINES,
                confidence=ConfidenceLevel.EXTRACTED,
                confidence_score=1.0,
                explanation=f"Document section hierarchy",
                line=line
            ))

            heading_stack.append((level, sec_id))

        # 提取文档中反引号提及的代码标识符，构建 Explains 关联
        for match in self.CODE_REF_RE.finditer(content):
            code_ident = match.group(1)
            line = content[:match.start()].count("\n") + 1
            if len(code_ident) > 3 and not code_ident.startswith("http"):
                edges.append(Edge(
                    source=file_node_id,
                    target=f"symbol:{code_ident}",
                    kind=EdgeKind.EXPLAINS,
                    confidence=ConfidenceLevel.INFERRED,
                    confidence_score=0.75,
                    explanation=f"Document references code identifier `{code_ident}`",
                    line=line
                ))

        return nodes, edges
