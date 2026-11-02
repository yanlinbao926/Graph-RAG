#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Graph-RAG 路径溯源与故障排查脚本 (Path & Debug CLI)
支持两大核心模式：
1. 节点诊断模式: python query_graph.py "<symbol>" (抓取爆炸半径、上下游调用)
2. 任意两点最短路径追踪 (对齐官方 graph-rag path): python query_graph.py "A" "B"
   例如: python query_graph.py "standalone_chat_endpoint" "robust_read_excel"
   输出: Shortest path (3 hops): A --calls--> B --calls--> C --calls--> D (Zero files opened)
"""

import sys
import json
import os
import argparse
from collections import deque
from typing import Dict, List, Any, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_graph(graph_json_path: str) -> Dict[str, Any]:
    if not os.path.exists(graph_json_path):
        raise FileNotFoundError(f"图谱文件未找到: {graph_json_path}")
    with open(graph_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_symbol_node(graph_data: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
    """根据关键词模糊或精确匹配节点"""
    matches = []
    kw_lower = keyword.lower().strip()
    for node in graph_data.get("nodes", []):
        nid = node.get("id", "").lower()
        name = node.get("name", "").lower()
        path = node.get("path", "").lower()
        if kw_lower == name or kw_lower == nid:
            matches.insert(0, node)
        elif kw_lower in name or kw_lower in nid or kw_lower in path:
            matches.append(node)
    return matches


def find_shortest_path(graph_data: Dict[str, Any], source_kw: str, target_kw: str) -> Optional[Dict[str, Any]]:
    """在图谱拓扑中寻找两点之间的最短调用/依赖路径 (Breadth-First Search)"""
    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])
    nodes_map = {n["id"]: n for n in nodes}

    src_matches = find_symbol_node(graph_data, source_kw)
    tgt_matches = find_symbol_node(graph_data, target_kw)

    if not src_matches:
        print(f"[-] 未找到起点符号: '{source_kw}'")
        return None
    if not tgt_matches:
        print(f"[-] 未找到终点符号: '{target_kw}'")
        return None

    src_node = src_matches[0]
    tgt_node = tgt_matches[0]

    if src_node["id"] == tgt_node["id"]:
        return {
            "source": src_node,
            "target": tgt_node,
            "hops": 0,
            "steps": [],
            "message": "起点与终点为同一个节点"
        }

    # 构建双向带方向标识的邻接网络
    adj: Dict[str, List[Tuple[str, str, str, str]]] = {n["id"]: [] for n in nodes}
    for e in links:
        s = e.get("source")
        t = e.get("target")
        k = e.get("kind", "relates")
        conf = e.get("confidence", "EXTRACTED")
        if s in adj and t in adj:
            adj[s].append((t, f"--{k}-->", k, conf))
            adj[t].append((s, f"<--{k}--", k, conf))

    queue = deque([(src_node["id"], [(src_node["id"], None, None, None)])])
    visited = {src_node["id"]}

    found_path = None
    while queue:
        curr, path_history = queue.popleft()
        if curr == tgt_node["id"]:
            found_path = path_history
            break

        for nxt, edge_label, kind, conf in adj.get(curr, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path_history + [(nxt, edge_label, kind, conf)]))

    if not found_path:
        return None

    hops = len(found_path) - 1
    steps = []
    for i in range(hops):
        from_id = found_path[i][0]
        to_id, edge_arrow, kind, conf = found_path[i+1]
        from_n = nodes_map.get(from_id, {})
        to_n = nodes_map.get(to_id, {})
        steps.append({
            "from_id": from_id,
            "from_name": from_n.get("name", from_id.split(":")[-1]),
            "from_path": from_n.get("path", ""),
            "from_line": from_n.get("line", 1),
            "to_id": to_id,
            "to_name": to_n.get("name", to_id.split(":")[-1]),
            "to_path": to_n.get("path", ""),
            "to_line": to_n.get("line", 1),
            "arrow": edge_arrow,
            "kind": kind,
            "confidence": conf
        })

    return {
        "source": src_node,
        "target": tgt_node,
        "hops": hops,
        "steps": steps
    }


def trace_blast_radius(graph_data: Dict[str, Any], target_id: str, max_depth: int = 2) -> Dict[str, Any]:
    """单节点波及范围 (爆炸半径与因果链条)"""
    links = graph_data.get("links", [])
    nodes_map = {n["id"]: n for n in graph_data.get("nodes", [])}

    upstream = []
    downstream = []

    for e in links:
        s = e.get("source")
        t = e.get("target")
        k = e.get("kind", "")
        if t == target_id:
            src_node = nodes_map.get(s, {"name": s, "path": "<unknown>", "line": 0})
            upstream.append({
                "caller_id": s,
                "name": src_node.get("name", s),
                "path": src_node.get("path", ""),
                "line": e.get("line", src_node.get("line", 0)),
                "kind": k,
                "confidence": e.get("confidence", "EXTRACTED")
            })
        if s == target_id:
            tgt_node = nodes_map.get(t, {"name": t, "path": "<unknown>", "line": 0})
            downstream.append({
                "callee_id": t,
                "name": tgt_node.get("name", t),
                "path": tgt_node.get("path", ""),
                "line": e.get("line", tgt_node.get("line", 0)),
                "kind": k,
                "confidence": e.get("confidence", "EXTRACTED")
            })

    target_node = nodes_map.get(target_id, {})
    return {
        "target": target_node,
        "upstream_callers": upstream,
        "downstream_callees": downstream,
        "blast_radius_score": len(upstream) + len(downstream),
        "is_god_node": target_node.get("degree", 0) >= 15
    }


def main():
    parser = argparse.ArgumentParser(description="Graph-RAG CLI & Multi-Hop Path Query")
    parser.add_argument("symbol_or_source", help="目标函数/符号名，或者寻路起点符号 (Source)")
    parser.add_argument("target", nargs="?", default=None, help="可选：寻路终点符号 (Target)。传入时触发任意两点最短路径追踪")
    parser.add_argument("--graph", "-g", default="./server_framework_graph/graph.json", help="知识图谱 graph.json 路径")
    parser.add_argument("--depth", "-d", type=int, default=2, help="追踪调用链路深度")

    args = parser.parse_args()

    # 尝试寻找有效的图谱文件
    graph_path = args.graph
    if not os.path.exists(graph_path):
        candidates = [
            "./server_framework_graph/graph.json",
            "./graph_rag_desktop_out/graph.json",
            "./graph_rag_out/graph.json"
        ]
        for c in candidates:
            if os.path.exists(c):
                graph_path = c
                break

    try:
        gdata = load_graph(graph_path)
    except Exception as e:
        print(f"[!] 无法加载图谱: {e}")
        print("    建议先执行: python -m app.graph_rag . --output ./server_framework_graph")
        sys.exit(1)

    # 模式 1：如果传入了两个参数，执行 Shortest Path 最短路径串联追踪
    if args.target:
        res = find_shortest_path(gdata, args.symbol_or_source, args.target)
        if not res:
            print(f"[-] 在图谱中未连通: '{args.symbol_or_source}' ➔ '{args.target}'")
            sys.exit(0)

        hops = res["hops"]
        src = res["source"]
        tgt = res["target"]
        print(f"\n$ graph-rag path \"{src['name']}\" \"{tgt['name']}\"\n")
        print(f"Shortest path ({hops} hops):")
        print(f"{src['name']} ({src.get('path', '')}:{src.get('line', 1)})")
        for s in res["steps"]:
            direction = s['arrow']
            to_n = s['to_name']
            to_loc = f"{s['to_path']}:{s['to_line']}"
            conf = f" [{s['confidence']}]" if s.get('confidence') else ""
            print(f"   {direction}{conf} {to_n} ({to_loc})")
        print(f"\n✨ {hops} hops. Zero files opened.\n")
        return

    # 模式 2：单节点诊断与上下游审计
    matches = find_symbol_node(gdata, args.symbol_or_source)
    if not matches:
        print(f"[-] 在知识图谱中未找到与 '{args.symbol_or_source}' 相关的节点。")
        sys.exit(0)

    best_match = matches[0]
    result = trace_blast_radius(gdata, best_match["id"], args.depth)

    target = result["target"]
    print(f"\n🎯 【目标故障节点锁定】: {target.get('name')} ({target.get('kind')})")
    print(f"   - 文件位置: {target.get('path')}:{target.get('line', 1)}")
    print(f"   - 所属子系统社区: Cluster #{target.get('community_id', -1)}")
    print(f"   - 架构中枢度数: {target.get('degree', 0)} ({'⚠️ God Node 核心枢纽，修改需格外谨慎!' if result['is_god_node'] else '普通业务节点'})\")")
    if target.get("docstring"):
        print(f"   - 注释说明: {target.get('docstring')}")

    print(f"\n🔍 【上游调用源头 (谁触发了该错误)】 (共 {len(result['upstream_callers'])} 个入口):")
    for up in result["upstream_callers"][:8]:
        print(f"   ▲ [{up['kind']}] {up['name']} ➔ 触发点位于 {up['path']}:{up['line']}")

    print(f"\n⚡ 【下游底层依赖 (执行抛错的具体底层)】 (共 {len(result['downstream_callees'])} 个依赖):")
    for down in result["downstream_callees"][:8]:
        print(f"   ▼ [{down['kind']}] {down['name']} ➔ 位于 {down['path']}:{down['line']}")

    print(f"\n💡 【排查建议】: 优先检查文件 `{target.get('path')}` 的第 {target.get('line', 1)} 行及上游传入参数是否异常。\n")


if __name__ == "__main__":
    main()
