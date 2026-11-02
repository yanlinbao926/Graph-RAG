"""
Graph-RAG 命令行执行入口 (CLI)
用法:
    python -m graph_rag [path_to_codebase] [--output output_dir]
"""

import argparse
import sys
import os
from . import scan_codebase


def main():
    parser = argparse.ArgumentParser(
        description="Graph-RAG: Turn codebases into deterministic queryable knowledge graphs (No Vector Store)."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target codebase directory (default: current directory)"
    )
    parser.add_argument(
        "--output", "-o",
        default="./graph_rag_out",
        help="Output directory for graph.json, GRAPH_REPORT.md, etc. (default: ./graph_rag_out)"
    )

    args = parser.parse_args()
    target_dir = os.path.abspath(args.target)
    out_dir = os.path.abspath(args.output)

    print(f"[*] Graph-RAG: Scanning codebase at '{target_dir}'...")
    graph, communities, insights, exported = scan_codebase(target_dir, out_dir)

    print(f"[+] Scan completed successfully!")
    print(f"    - Nodes: {insights.total_nodes}")
    print(f"    - Edges: {insights.total_edges}")
    print(f"    - Communities: {len(communities)} clusters")
    print(f"    - Confidence: EXTRACTED={insights.confidence_distribution.get('EXTRACTED', 0)}, INFERRED={insights.confidence_distribution.get('INFERRED', 0)}")

    if insights.god_nodes:
        print(f"    - Top God Node: {insights.god_nodes[0]['name']} (Degree: {insights.god_nodes[0]['degree']})")

    if exported:
        print(f"[+] Artifacts written to: {out_dir}")
        for k, p in exported.items():
            print(f"    - {k}: {p}")


if __name__ == "__main__":
    main()
