from __future__ import annotations

"""
REQ_1_4 A* 算法走迷宫

独立 OJ 脚本：
- 从标准输入读取迷宫
- 维护 g / h / f
- 使用优先队列按 f 最小扩展节点
- 使用 parent 回溯路径
- 找不到路径时输出 NO
"""

import heapq
import sys
from typing import Dict, List, Optional, Set, Tuple

Pos = Tuple[int, int]
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def is_walkable(ch: str) -> bool:
    return ch != '#'


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


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


def solve_astar(grid: List[str], start: Pos, end: Pos) -> Optional[List[Pos]]:
    n, m = len(grid), len(grid[0])
    g = [[10 ** 18] * m for _ in range(n)]
    g[start[0]][start[1]] = 0
    parent: Dict[Pos, Optional[Pos]] = {start: None}
    open_heap: List[Tuple[int, int, Pos]] = [(manhattan(start, end), 0, start)]
    closed: Set[Pos] = set()

    while open_heap:
        f, cur_g, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        if cur == end:
            return reconstruct(parent, end)
        closed.add(cur)

        r, c = cur
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)
            if not (0 <= nr < n and 0 <= nc < m):
                continue
            if not is_walkable(grid[nr][nc]):
                continue
            if nxt in closed:
                continue

            tentative_g = cur_g + 1
            if tentative_g < g[nr][nc]:
                g[nr][nc] = tentative_g
                parent[nxt] = cur
                h = manhattan(nxt, end)
                heapq.heappush(open_heap, (tentative_g + h, tentative_g, nxt))

    return None


def main() -> None:
    grid, start, end = read_input()
    path = solve_astar(grid, start, end)
    if path is None:
        print("NO")
        return
    print(len(path))
    for r, c in path:
        print(r, c)


if __name__ == '__main__':
    main()
