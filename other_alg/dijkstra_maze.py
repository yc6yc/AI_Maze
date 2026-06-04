from __future__ import annotations

"""
REQ_1_3 Dijkstra 算法走迷宫

独立 OJ 脚本：
- 从标准输入读取迷宫
- 将可通行格建模为图节点
- 使用 Dijkstra 求 S 到 E 的最短路径
- 使用 parent 回溯输出完整坐标序列
"""

import heapq
import sys
from typing import Dict, List, Optional, Tuple

Pos = Tuple[int, int]
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def is_walkable(ch: str) -> bool:
    return ch != '#'


def read_input() -> Tuple[List[str], Pos, Pos]:
    data = sys.stdin.read().strip().splitlines()
    if not data:
        raise ValueError("empty input")
    data[0] = data[0].lstrip("\ufeff")
    n, m = map(int, data[0].split())
    grid = [line.rstrip("\n") for line in data[1:1 + n]]
    start = end = None
    for r in range(n):
        for c in range(m):
            if grid[r][c] == 'S':
                start = (r, c)
            elif grid[r][c] == 'E':
                end = (r, c)
    if start is None or end is None:
        raise ValueError("maze must contain S and E")
    return grid, start, end


def reconstruct(parent: Dict[Pos, Optional[Pos]], end: Pos) -> List[Pos]:
    path: List[Pos] = []
    cur: Optional[Pos] = end
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


def solve_dijkstra(grid: List[str], start: Pos, end: Pos) -> List[Pos]:
    n, m = len(grid), len(grid[0])
    inf = 10 ** 18
    dist = [[inf] * m for _ in range(n)]
    parent: Dict[Pos, Optional[Pos]] = {start: None}
    heap: List[Tuple[int, Pos]] = [(0, start)]
    dist[start[0]][start[1]] = 0

    while heap:
        d, cur = heapq.heappop(heap)
        if d != dist[cur[0]][cur[1]]:
            continue
        if cur == end:
            break
        r, c = cur
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m and is_walkable(grid[nr][nc]):
                nd = d + 1
                if nd < dist[nr][nc]:
                    dist[nr][nc] = nd
                    parent[(nr, nc)] = cur
                    heapq.heappush(heap, (nd, (nr, nc)))

    if dist[end[0]][end[1]] == inf:
        return []
    return reconstruct(parent, end)


def main() -> None:
    grid, start, end = read_input()
    path = solve_dijkstra(grid, start, end)
    print(len(path))
    for r, c in path:
        print(r, c)


if __name__ == '__main__':
    main()
