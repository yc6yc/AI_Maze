from __future__ import annotations

"""
REQ_1_2 分支限界算法走迷宫

独立 OJ 脚本：
- 从标准输入读取迷宫
- 使用分支限界搜索 S 到 E 的路径
- 维护当前最优路径长度 best_len
- 使用 lower_bound = current_steps + ManhattanDistance(current, end) 剪枝
"""

from typing import List, Optional, Set, Tuple
import sys

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


def solve_branch_and_bound(grid: List[str], start: Pos, end: Pos) -> List[Pos]:
    n, m = len(grid), len(grid[0])
    best_len = float('inf')
    best_path: List[Pos] = []
    seen_best = {}

    def dfs(cur: Pos, path: List[Pos], visited: Set[Pos]) -> None:
        nonlocal best_len, best_path
        steps = len(path) - 1
        lower_bound = steps + manhattan(cur, end)
        if lower_bound >= best_len:
            return

        if steps >= seen_best.get(cur, float('inf')):
            return
        seen_best[cur] = steps

        if cur == end:
            best_len = len(path)
            best_path = path[:]
            return

        r, c = cur
        candidates = []
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)
            if 0 <= nr < n and 0 <= nc < m and is_walkable(grid[nr][nc]) and nxt not in visited:
                candidates.append(nxt)

        candidates.sort(key=lambda p: manhattan(p, end))
        for nxt in candidates:
            visited.add(nxt)
            path.append(nxt)
            dfs(nxt, path, visited)
            path.pop()
            visited.remove(nxt)

    dfs(start, [start], {start})
    return best_path


def main() -> None:
    grid, start, end = read_input()
    path = solve_branch_and_bound(grid, start, end)
    print(len(path))
    for r, c in path:
        print(r, c)


if __name__ == '__main__':
    main()
