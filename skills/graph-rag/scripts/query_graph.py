#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Graph-Guided Debugger 辅助查询脚本
用于在代码出现故障或报错时，快速从构建好的 graph.json 或全库中精准定位问题节点及上下游调用链路
"""

import sys
import json
import os
import argparse
from typing import Dict, List, Any

# 确保在 Windows 控制台或管道下 UTF-8 安全输出
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
            matches.insert(0, node) # 精确匹配放首位
        elif kw_lower in name or kw_lower in nid or kw_lower in path:
            matches.append(node)
    return matches


def trace_blast_radius(graph_data: Dict[str, Any], target_id: str, max_depth: int = 2) -> Dict[str, Any]:
    """分析故障节点的波及范围 (爆炸半径与因果链条)"""
    links = graph_data.get("links", [])
    nodes_map = {n["id"]: n for n in graph_data.get("nodes", [])}

    # 上游调用者 (In-degree callers: 谁调用了它)
    upstream = []
    # 下游依赖 (Out-degree callees: 它调用了谁)
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
    parser = argparse.ArgumentParser(description="Graph-Guided Debugger CLI")
    parser.add_argument("keyword", help="报错或异常涉及的函数名、类名、文件名或报错关键字")
    parser.add_argument("--graph", "-g", default="./graph_rag_out/graph.json", help="知识图谱 graph.json 路径")
    parser.add_argument("--depth", "-d", type=int, default=2, help="追踪调用链路深度")

    args = parser.parse_args()

    try:
        gdata = load_graph(args.graph)
    except Exception as e:
        print(f"[!] 无法加载图谱: {e}")
        print("    建议先执行: python -m graph_rag . --output ./graph_rag_out")
        sys.exit(1)

    matches = find_symbol_node(gdata, args.keyword)
    if not matches:
        print(f"[-] 在知识图谱中未找到与 '{args.keyword}' 相关的节点。")
        sys.exit(0)

    best_match = matches[0]
    result = trace_blast_radius(gdata, best_match["id"], args.depth)

    target = result["target"]
    print(f"\n🎯 【目标故障节点锁定】: {target.get('name')} ({target.get('kind')})")
    print(f"   - 文件位置: {target.get('path')}:{target.get('line', 1)}")
    print(f"   - 所属子系统社区: Cluster #{target.get('community_id', -1)}")
    print(f"   - 架构中枢度数: {target.get('degree', 0)} ({'⚠️ God Node 核心枢纽，修改需格外谨慎!' if result['is_god_node'] else '普通业务节点'})")
    if target.get('docstring'):
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
