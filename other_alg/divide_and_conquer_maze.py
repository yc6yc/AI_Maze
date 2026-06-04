from __future__ import annotations

"""
REQ_1_1 分治算法走迷宫

独立 OJ 脚本：
- 从标准输入读取迷宫
- 使用“区域划分 + 递归求解 + 子路径合并”的分治思想寻找 S 到 E 的唯一路径
- 小区域退化为 BFS 求解

说明：
题目保证所有可通行格子连通，且任意两点之间只有一条简单路径。
本实现仍显式体现分治结构：
1. 对当前矩形区域进行纵切或横切；
2. 寻找跨分割线的连接边；
3. 判断 start/end 位于同侧还是异侧；
4. 递归求解子区域路径并拼接。
"""

from collections import deque
from typing import Deque, Dict, List, Optional, Tuple
import sys

Pos = Tuple[int, int]
Rect = Tuple[int, int, int, int]  # top, bottom, left, right
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BASE_AREA_THRESHOLD = 25


def is_walkable(ch: str) -> bool:
    return ch != "#"


def inside_rect(pos: Pos, rect: Rect) -> bool:
    r, c = pos
    top, bottom, left, right = rect
    return top <= r <= bottom and left <= c <= right


def neighbors_in_rect(pos: Pos, grid: List[str], rect: Rect):
    r, c = pos
    top, bottom, left, right = rect
    for dr, dc in DIRS:
        nr, nc = r + dr, c + dc
        if top <= nr <= bottom and left <= nc <= right and is_walkable(grid[nr][nc]):
            yield (nr, nc)


def bfs_path_in_rect(grid: List[str], start: Pos, end: Pos, rect: Rect) -> Optional[List[Pos]]:
    queue: Deque[Pos] = deque([start])
    parent: Dict[Pos, Optional[Pos]] = {start: None}

    while queue:
        cur = queue.popleft()
        if cur == end:
            return reconstruct_path(parent, end)
        for nxt in neighbors_in_rect(cur, grid, rect):
            if nxt not in parent:
                parent[nxt] = cur
                queue.append(nxt)
    return None


def reconstruct_path(parent: Dict[Pos, Optional[Pos]], end: Pos) -> List[Pos]:
    path: List[Pos] = []
    cur: Optional[Pos] = end
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


def rect_area(rect: Rect) -> int:
    top, bottom, left, right = rect
    return (bottom - top + 1) * (right - left + 1)


def split_rect(rect: Rect) -> Tuple[str, int]:
    top, bottom, left, right = rect
    height = bottom - top + 1
    width = right - left + 1
    if width >= height:
        return ("V", (left + right) // 2)
    return ("H", (top + bottom) // 2)


def partition_rect(rect: Rect, axis: str, cut: int) -> Tuple[Rect, Rect]:
    top, bottom, left, right = rect
    if axis == "V":
        return (top, bottom, left, cut), (top, bottom, cut + 1, right)
    return (top, cut, left, right), (cut + 1, bottom, left, right)


def crossing_edges(grid: List[str], rect: Rect, axis: str, cut: int) -> List[Tuple[Pos, Pos]]:
    top, bottom, left, right = rect
    edges: List[Tuple[Pos, Pos]] = []
    if axis == "V":
        if cut < left or cut >= right:
            return edges
        for r in range(top, bottom + 1):
            a = (r, cut)
            b = (r, cut + 1)
            if is_walkable(grid[a[0]][a[1]]) and is_walkable(grid[b[0]][b[1]]):
                edges.append((a, b))
    else:
        if cut < top or cut >= bottom:
            return edges
        for c in range(left, right + 1):
            a = (cut, c)
            b = (cut + 1, c)
            if is_walkable(grid[a[0]][a[1]]) and is_walkable(grid[b[0]][b[1]]):
                edges.append((a, b))
    return edges


def merge_paths(path1: List[Pos], path2: List[Pos]) -> List[Pos]:
    if not path1:
        return path2
    if not path2:
        return path1
    if path1[-1] == path2[0]:
        return path1 + path2[1:]
    return path1 + path2


def solve_divide_and_conquer(grid: List[str], start: Pos, end: Pos, rect: Rect) -> Optional[List[Pos]]:
    if start == end:
        return [start]

    if rect_area(rect) <= BASE_AREA_THRESHOLD:
        return bfs_path_in_rect(grid, start, end, rect)

    axis, cut = split_rect(rect)
    left_rect, right_rect = partition_rect(rect, axis, cut)

    start_in_left = inside_rect(start, left_rect)
    end_in_left = inside_rect(end, left_rect)

    if start_in_left == end_in_left:
        sub_rect = left_rect if start_in_left else right_rect
        return solve_divide_and_conquer(grid, start, end, sub_rect)

    bridges = crossing_edges(grid, rect, axis, cut)
    for a, b in bridges:
        if start_in_left:
            left_entry, right_entry = a, b
        else:
            left_entry, right_entry = b, a

        path1 = solve_divide_and_conquer(grid, start, left_entry, left_rect if start_in_left else right_rect)
        if path1 is None:
            continue
        path2 = solve_divide_and_conquer(grid, right_entry, end, right_rect if start_in_left else left_rect)
        if path2 is None:
            continue
        return merge_paths(path1, path2)

    return bfs_path_in_rect(grid, start, end, rect)


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
            if grid[r][c] == "S":
                start = (r, c)
            elif grid[r][c] == "E":
                end = (r, c)
    if start is None or end is None:
        raise ValueError("maze must contain S and E")
    return grid, start, end


def main() -> None:
    grid, start, end = read_input()
    rect = (0, len(grid) - 1, 0, len(grid[0]) - 1)
    path = solve_divide_and_conquer(grid, start, end, rect)
    if path is None:
        print(0)
        return
    print(len(path))
    for r, c in path:
        print(r, c)


if __name__ == "__main__":
    main()
