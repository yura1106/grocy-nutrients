#!/usr/bin/env python3
"""Build a compact index.json lookup next to each graphify graph.json.

graphify's CLI only emits graph.json (full node/edge graph). This derives a
small lookup — {node -> {kind, src, loc, community, block_id, out, in}} — that
an agent can Read in one shot to resolve definitions and traverse edges without
loading the multi-MB raw graph.

Usage:
    python3 scripts/graphify_index.py backend/graphify-out frontend/graphify-out
    python3 scripts/graphify_index.py            # defaults to both app dirs
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIRS = [ROOT / "backend" / "graphify-out", ROOT / "frontend" / "graphify-out"]


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\-. ]+", "_", name.strip(), flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    if not s:
        s = "node"
    if len(s) > 120:
        h = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
        s = s[:100].rstrip() + " " + h
    return s


def load_graph(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Unsupported graph format in {path}")
    return data.get("nodes", []), data.get("edges", data.get("links", []))


def node_name(node) -> str:
    for key in ("label", "id", "name", "title"):
        if key in node and node[key]:
            return str(node[key])
    return "unknown-node"


def edge_endpoints(edge):
    src = edge.get("source", edge.get("from", edge.get("src")))
    dst = edge.get("target", edge.get("to", edge.get("dst")))
    rel = edge.get("type", edge.get("label", edge.get("relation", "related_to")))
    meta = []
    if edge.get("provenance"):
        meta.append(str(edge["provenance"]))
    if edge.get("context"):
        meta.append(f"context={edge['context']}")
    return src, dst, rel, ", ".join(meta)


def build_index(graph_path: Path) -> dict:
    nodes, edges = load_graph(graph_path)
    by_name = {}
    for n in nodes:
        nm = node_name(n)
        by_name[nm] = {
            "kind": n.get("kind", n.get("type", "node")),
            "src": n.get("src", ""),
            "loc": n.get("loc", ""),
            "community": str(n.get("community", "")),
        }

    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for e in edges:
        src, dst, rel, meta = edge_endpoints(e)
        if src in by_name and dst in by_name:
            outgoing[src].append({"rel": rel, "target": dst, "meta": meta})
            incoming[dst].append({"rel": rel, "source": src, "meta": meta})

    communities = {info["community"] for info in by_name.values()}
    return {
        "meta": {
            "source_graph": graph_path.name,
            "node_count": len(by_name),
            "edge_count": len(edges),
            "community_count": len(communities),
        },
        "nodes": {
            nm: {
                **info,
                "block_id": slugify(nm),
                "out": outgoing.get(nm, []),
                "in": incoming.get(nm, []),
            }
            for nm, info in by_name.items()
        },
    }


def main() -> None:
    args = sys.argv[1:]
    dirs = [Path(a) for a in args] if args else DEFAULT_DIRS
    for d in dirs:
        graph_path = d / "graph.json"
        if not graph_path.exists():
            print(f"skip: no graph.json in {d}", file=sys.stderr)
            continue
        index = build_index(graph_path)
        out = d / "index.json"
        out.write_text(
            json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        meta = index["meta"]
        print(f"wrote {out} ({meta['node_count']} nodes, {meta['edge_count']} edges)")


if __name__ == "__main__":
    main()
