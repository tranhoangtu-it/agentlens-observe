"""Span tree diff algorithm for trace comparison.

Matches spans between two traces by (name, type, depth, sibling_index) tuple.
Returns categorized matches: identical, changed, left_only, right_only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SpanNode:
    """Span with tree metadata for matching."""
    span_id: str
    name: str
    type: str
    depth: int
    sibling_index: int
    input: Optional[str]
    output: Optional[str]
    start_ms: Optional[int]
    end_ms: Optional[int]
    cost_usd: Optional[float]
    cost_input_tokens: Optional[int]
    cost_output_tokens: Optional[int]
    children: list["SpanNode"]


def build_span_tree(spans: list[dict]) -> list[SpanNode]:
    """Convert flat span list to nested tree of SpanNode objects.

    Returns root nodes (spans without parent_id or with unknown parent).
    """
    by_id: dict[str, SpanNode] = {}
    children_map: dict[str, list[str]] = {}

    # Build id -> node map
    for s in spans:
        sid = s.get("id") or s.get("span_id", "")
        node = SpanNode(
            span_id=sid,
            name=s.get("name", ""),
            type=s.get("type", ""),
            depth=0,
            sibling_index=0,
            input=s.get("input"),
            output=s.get("output"),
            start_ms=s.get("start_ms"),
            end_ms=s.get("end_ms"),
            cost_usd=s.get("cost_usd"),
            cost_input_tokens=s.get("cost_input_tokens"),
            cost_output_tokens=s.get("cost_output_tokens"),
            children=[],
        )
        by_id[sid] = node
        parent_id = s.get("parent_id")
        if parent_id:
            children_map.setdefault(parent_id, []).append(sid)

    # Attach children and assign sibling indexes
    for parent_id, child_ids in children_map.items():
        if parent_id in by_id:
            for idx, cid in enumerate(child_ids):
                if cid in by_id:
                    by_id[cid].sibling_index = idx
                    by_id[parent_id].children.append(by_id[cid])

    # Find roots (no parent or parent not in tree)
    all_ids = set(by_id.keys())
    parent_ids = set()
    for s in spans:
        pid = s.get("parent_id")
        if pid:
            parent_ids.add(pid)

    root_ids = [sid for sid in all_ids if not any(
        s.get("parent_id") == sid or (s.get("id") == sid and not s.get("parent_id"))
        for s in spans
    )]

    # Simpler root detection: spans whose parent_id is None or not in tree
    roots = []
    for s in spans:
        sid = s.get("id") or s.get("span_id", "")
        parent_id = s.get("parent_id")
        if not parent_id or parent_id not in by_id:
            roots.append(by_id[sid])

    # Assign depths
    def assign_depths(node: SpanNode, depth: int) -> None:
        node.depth = depth
        for child in node.children:
            assign_depths(child, depth + 1)

    for root in roots:
        assign_depths(root, 0)

    return roots


def _flatten_tree(roots: list[SpanNode]) -> list[SpanNode]:
    """DFS flatten tree back to ordered list."""
    result: list[SpanNode] = []

    def dfs(node: SpanNode) -> None:
        result.append(node)
        for child in node.children:
            dfs(child)

    for root in roots:
        dfs(root)
    return result


def match_spans(
    left_roots: list[SpanNode],
    right_roots: list[SpanNode],
) -> tuple[list[tuple[SpanNode, SpanNode]], list[SpanNode], list[SpanNode]]:
    """Match spans by (name, type, depth, sibling_index).

    Returns (matched_pairs, left_only, right_only).
    """
    left_flat = _flatten_tree(left_roots)
    right_flat = _flatten_tree(right_roots)

    # Build match key -> list of nodes (allow duplicates with order)
    def match_key(n: SpanNode) -> tuple:
        return (n.name, n.type, n.depth, n.sibling_index)

    # Group right nodes by key
    right_by_key: dict[tuple, list[SpanNode]] = {}
    for node in right_flat:
        k = match_key(node)
        right_by_key.setdefault(k, []).append(node)

    matched: list[tuple[SpanNode, SpanNode]] = []
    left_only: list[SpanNode] = []
    used_right: set[str] = set()

    for left_node in left_flat:
        k = match_key(left_node)
        candidates = right_by_key.get(k, [])
        # Pick first unused candidate
        matched_right = None
        for candidate in candidates:
            if candidate.span_id not in used_right:
                matched_right = candidate
                used_right.add(candidate.span_id)
                break

        if matched_right:
            matched.append((left_node, matched_right))
        else:
            left_only.append(left_node)

    right_only = [n for n in right_flat if n.span_id not in used_right]

    return matched, left_only, right_only


def compute_diff(left_spans: list[dict], right_spans: list[dict]) -> dict:
    """Compute full diff between two span lists.

    Returns dict with matched, left_only, right_only lists.
    Each matched entry has left_span_id, right_span_id, status (identical|changed).
    Deltas include duration_delta_ms, cost_delta_usd, input_tokens_delta, output_tokens_delta.
    """
    left_roots = build_span_tree(left_spans)
    right_roots = build_span_tree(right_spans)

    matched_pairs, left_only, right_only = match_spans(left_roots, right_roots)

    def spans_identical(a: SpanNode, b: SpanNode) -> bool:
        return a.input == b.input and a.output == b.output

    def duration(n: SpanNode) -> Optional[int]:
        if n.start_ms is not None and n.end_ms is not None:
            return n.end_ms - n.start_ms
        return None

    matched_result = []
    for left_node, right_node in matched_pairs:
        left_dur = duration(left_node)
        right_dur = duration(right_node)
        dur_delta = None
        if left_dur is not None and right_dur is not None:
            dur_delta = right_dur - left_dur

        cost_delta = None
        if left_node.cost_usd is not None and right_node.cost_usd is not None:
            cost_delta = right_node.cost_usd - left_node.cost_usd

        input_tokens_delta = None
        if left_node.cost_input_tokens is not None and right_node.cost_input_tokens is not None:
            input_tokens_delta = right_node.cost_input_tokens - left_node.cost_input_tokens

        output_tokens_delta = None
        if left_node.cost_output_tokens is not None and right_node.cost_output_tokens is not None:
            output_tokens_delta = right_node.cost_output_tokens - left_node.cost_output_tokens

        matched_result.append({
            "left_span_id": left_node.span_id,
            "right_span_id": right_node.span_id,
            "status": "identical" if spans_identical(left_node, right_node) else "changed",
            "duration_delta_ms": dur_delta,
            "cost_delta_usd": cost_delta,
            "input_tokens_delta": input_tokens_delta,
            "output_tokens_delta": output_tokens_delta,
        })

    return {
        "matched": matched_result,
        "left_only": [n.span_id for n in left_only],
        "right_only": [n.span_id for n in right_only],
    }
