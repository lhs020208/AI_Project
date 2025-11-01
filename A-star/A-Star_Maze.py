from pico2d import *
import heapq
from itertools import count

class Node:
    def __init__(self, x=0, y=0, state=0):
        self.x = x
        self.y = y
        self.state = state
        self.g = float('inf')
        self.h = 0
        self.f = float('inf')
        self.parent = None

def manhattan(a, b):
    return abs(a.x - b.x) + abs(a.y - b.y)

def get_neighbors(node, grid):
    directions = [(0,1), (1,0), (0,-1), (-1,0)]
    neighbors = []
    for dx, dy in directions:
        nx, ny = node.x + dx, node.y + dy
        if 0 <= nx < 20 and 0 <= ny < 20:
            neighbor = grid[nx][ny]
            if neighbor.state != 1:  # 벽은 통과 불가
                neighbors.append(neighbor)
    return neighbors
def reset_nodes_and_marks():
    for i in range(20):
        for j in range(20):
            n = grid[i][j]
            n.g = float('inf'); n.h = 0; n.f = float('inf'); n.parent = None
            if n.state in (2, 3, 4):   # 시각화 흔적(열림/닫힘/경로) 초기화
                n.state = 0

def find_start_goal():
    s = g = None
    for i in range(20):
        for j in range(20):
            n = grid[i][j]
            if n.state == 10: s = n
            elif n.state == 20: g = n
    return s, g

def start_astar():
    global algo_running, start_node, goal_node, open_heap, closed_set
    reset_nodes_and_marks()
    start_node, goal_node = find_start_goal()
    if not (start_node and goal_node):
        return  # 시작/도착 미지정 시 무시
    open_heap = []
    closed_set = set()
    start_node.g = 0
    start_node.h = manhattan(start_node, goal_node)
    start_node.f = start_node.h
    heapq.heappush(open_heap, (start_node.f, next(counter), start_node))
    algo_running = True

def step_astar():
    global algo_running
    if not open_heap:
        algo_running = False
        return

    # F 최소 노드 팝
    current = heapq.heappop(open_heap)[2]

    # 도착 도달 → 경로 복원(보라, state=4) 후 종료
    if current is goal_node:
        p = current.parent
        while p and p is not start_node:
            p.state = 4  # Path (Purple)
            p = p.parent
        algo_running = False
        return

    closed_set.add(current)
    if current is not start_node and current is not goal_node and current.state != 4:
        current.state = 2

    # 이웃 갱신
    for nb in get_neighbors(current, grid):
        if nb in closed_set:
            continue
        tentative_g = current.g + 1
        if tentative_g < nb.g:
            nb.parent = current
            nb.g = tentative_g
            nb.h = manhattan(nb, goal_node)
            nb.f = nb.g + nb.h
            heapq.heappush(open_heap, (nb.f, next(counter), nb))
            if nb is not start_node and nb is not goal_node:
                nb.state = 3

# 초기화
open_canvas(400, 400)

# 노드 이미지 로드 (20x20 크기)
white_node_img = load_image("WhiteNode.png")
Black_node_img = load_image("BlackNode.png")
red_node_img = load_image("RedNode.png")
green_node_img = load_image("GreenNode.png")
blue_node_img = load_image("BlueNode.png")
yellow_node_img = load_image("YellowNode.png")
Purple_node_img = load_image("PurpleNode.png")

# 20x20 그리드 생성
grid = [[Node(i, j, 0) for j in range(20)] for i in range(20)]

# 마우스 상태 변수
left_pressed = False
right_pressed = False
LeftClickNum = 0

# A* 알고리즘 변수
counter = count()
algo_running = False
start_node = None
goal_node = None
open_heap = []
closed_set = set()

# 메인 루프
running = True
while running:
    if algo_running:
        step_astar()
    clear_canvas()

    for i in range(20):
        for j in range(20):
            node = grid[i][j]
            x = node.x * 20 + 10   # 중심 x
            y = node.y * 20 + 10   # 중심 y

            if node.state == 0:
                white_node_img.draw(x, y)
            elif node.state == 1:
                Black_node_img.draw(x, y)
            elif node.state == 2:
                red_node_img.draw(x, y)
            elif node.state == 3:
                green_node_img.draw(x, y)
            elif node.state == 4:
                Purple_node_img.draw(x, y)
            elif node.state == 10:
                yellow_node_img.draw(x, y)
            elif node.state == 20:
                blue_node_img.draw(x, y)

    update_canvas()

    # --- 이벤트 처리 ---
    for e in get_events():
        # 종료
        if e.type == SDL_QUIT or (e.type == SDL_KEYDOWN and e.key == SDLK_ESCAPE):
            running = False
        elif e.type == SDL_KEYDOWN and e.key == SDLK_a:
            for i in range(20):
                for j in range(20):
                    node = grid[i][j]
                    if node.state == 10 or node.state == 20:
                        node.state = 0
            LeftClickNum = 0
        elif e.type == SDL_KEYDOWN and e.key == SDLK_SPACE:
            start_astar()  # 스페이스로 A* 시작
        elif e.type == SDL_KEYDOWN and e.key == SDLK_c:
            # 전체 초기화
            for i in range(20):
                for j in range(20):
                    n = grid[i][j]
                    n.state = 0
                    n.g = float('inf');
                    n.h = 0;
                    n.f = float('inf');
                    n.parent = None
            LeftClickNum = 0
            algo_running = False
            open_heap.clear()
            closed_set.clear()

        # 좌클릭 시작 (누름)
        elif e.type == SDL_MOUSEBUTTONDOWN and e.button == SDL_BUTTON_LEFT:
            numx = e.x // 20
            numy = 20 - (e.y // 20) - 1
            if not (0 <= numx < 20 and 0 <= numy < 20):
                continue
            node = grid[numx][numy]

            if LeftClickNum == 0 and node.state == 0:
                node.state = 10  # Start
                LeftClickNum = 1
            elif LeftClickNum == 1 and node.state == 0:
                node.state = 20  # Goal
                LeftClickNum = 2
            elif LeftClickNum == 2:
                left_pressed = True
                if node.state == 0:
                    node.state = 1  # 벽 생성

        # 좌클릭 드래그 (벽 그리기)
        elif e.type == SDL_MOUSEMOTION and left_pressed and LeftClickNum == 2:
            numx = e.x // 20
            numy = 20 - (e.y // 20) - 1
            if 0 <= numx < 20 and 0 <= numy < 20:
                node = grid[numx][numy]
                if node.state == 0:
                    node.state = 1

        # 좌클릭 해제
        elif e.type == SDL_MOUSEBUTTONUP and e.button == SDL_BUTTON_LEFT:
            left_pressed = False

        # 우클릭 (지우기)
        elif e.type == SDL_MOUSEBUTTONDOWN and e.button == SDL_BUTTON_RIGHT:
            right_pressed = True
            numx = e.x // 20
            numy = 20 - (e.y // 20) - 1
            if not (0 <= numx < 20 and 0 <= numy < 20):
                continue
            node = grid[numx][numy]
            if node.state == 1:
                node.state = 0

        # 우클릭 드래그 (연속 지우기)
        elif e.type == SDL_MOUSEMOTION and right_pressed:
            numx = e.x // 20
            numy = 20 - (e.y // 20) - 1
            if 0 <= numx < 20 and 0 <= numy < 20:
                node = grid[numx][numy]
                if node.state == 1:
                    node.state = 0

        # 우클릭 해제
        elif e.type == SDL_MOUSEBUTTONUP and e.button == SDL_BUTTON_RIGHT:
            right_pressed = False

close_canvas()
