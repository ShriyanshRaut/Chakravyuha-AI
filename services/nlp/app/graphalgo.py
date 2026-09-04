from __future__ import annotations
from typing import Any, Dict, List, Set, Tuple
from collections import deque

class Graph:

    def __init__(self):
        self.adj: Dict[str, Dict[str, float]] = {}

    def add_node(self, n: str) -> None:
        self.adj.setdefault(n, {})

    def add_edge(self, a: str, b: str, weight: float=1.0) -> None:
        if a == b:
            return
        self.add_node(a)
        self.add_node(b)
        self.adj[a][b] = weight
        self.adj[b][a] = weight

    def nodes(self) -> List[str]:
        return sorted(self.adj)

    def neighbors(self, n: str) -> List[str]:
        return sorted(self.adj[n])

    def degree(self) -> Dict[str, int]:
        return {n: len(self.adj[n]) for n in self.adj}

    def number_of_nodes(self) -> int:
        return len(self.adj)

    def number_of_edges(self) -> int:
        return sum((len(v) for v in self.adj.values())) // 2

    def edges(self) -> List[Tuple[str, str, float]]:
        seen, out = (set(), [])
        for a in self.nodes():
            for b in self.neighbors(a):
                if (b, a) not in seen:
                    seen.add((a, b))
                    out.append((a, b, self.adj[a][b]))
        return out

def pagerank(g: Graph, alpha: float=0.85, iterations: int=100, tol: float=1e-09) -> Dict[str, float]:
    nodes = g.nodes()
    n = len(nodes)
    if n == 0:
        return {}
    rank = {v: 1.0 / n for v in nodes}
    strength = {v: sum(g.adj[v].values()) for v in nodes}
    for _ in range(iterations):
        nxt = {v: (1.0 - alpha) / n for v in nodes}
        dangling = 0.0
        for v in nodes:
            if strength[v] == 0:
                dangling += rank[v]
                continue
            for u, w in g.adj[v].items():
                nxt[u] += alpha * rank[v] * w / strength[v]
        if dangling:
            share = alpha * dangling / n
            for v in nodes:
                nxt[v] += share
        delta = sum((abs(nxt[v] - rank[v]) for v in nodes))
        rank = nxt
        if delta < tol * n:
            break
    total = sum(rank.values()) or 1.0
    return {v: rank[v] / total for v in nodes}

def betweenness_centrality(g: Graph, normalized: bool=True) -> Dict[str, float]:
    nodes = g.nodes()
    bc = {v: 0.0 for v in nodes}
    for s in nodes:
        stack: List[str] = []
        preds: Dict[str, List[str]] = {v: [] for v in nodes}
        sigma = {v: 0.0 for v in nodes}
        dist = {v: -1 for v in nodes}
        sigma[s] = 1.0
        dist[s] = 0
        q = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            for w in g.neighbors(v):
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    preds[w].append(v)
        delta = {v: 0.0 for v in nodes}
        while stack:
            w = stack.pop()
            for v in preds[w]:
                delta[v] += sigma[v] / sigma[w] * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]
    n = len(nodes)
    if normalized and n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        bc = {v: c * scale * 2.0 for v, c in bc.items()}
    else:
        bc = {v: c / 2.0 for v, c in bc.items()}
    return bc

def connected_components(g: Graph) -> List[List[str]]:
    seen: Set[str] = set()
    out = []
    for s in g.nodes():
        if s in seen:
            continue
        comp, q = ([], deque([s]))
        seen.add(s)
        while q:
            v = q.popleft()
            comp.append(v)
            for w in g.neighbors(v):
                if w not in seen:
                    seen.add(w)
                    q.append(w)
        out.append(sorted(comp))
    return sorted(out, key=lambda c: (-len(c), c[0]))

def _modularity(g: Graph, groups: List[Set[str]]) -> float:
    m = sum((w for _, _, w in g.edges()))
    if m == 0:
        return 0.0
    q = 0.0
    for grp in groups:
        inside = 0.0
        tot = 0.0
        for v in grp:
            for u, w in g.adj[v].items():
                tot += w
                if u in grp:
                    inside += w
        q += inside / (2 * m) - (tot / (2 * m)) ** 2
    return q

def greedy_modularity_communities(g: Graph) -> List[List[str]]:
    groups = [{v} for v in g.nodes()]
    best = _modularity(g, groups)
    improved = True
    while improved and len(groups) > 1:
        improved = False
        best_pair, best_q = (None, best)
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if not any((u in groups[j] for v in groups[i] for u in g.adj[v])):
                    continue
                merged = groups[:i] + groups[i + 1:j] + groups[j + 1:] + [groups[i] | groups[j]]
                q = _modularity(g, merged)
                if q > best_q + 1e-12:
                    best_q, best_pair = (q, (i, j))
        if best_pair:
            i, j = best_pair
            groups = groups[:i] + groups[i + 1:j] + groups[j + 1:] + [groups[i] | groups[j]]
            best = best_q
            improved = True
    return sorted([sorted(gp) for gp in groups], key=lambda c: (-len(c), c[0]))