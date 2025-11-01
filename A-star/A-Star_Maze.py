from pico2d import *
import heapq

class Node:
    """
    state:
    0: Empty
    1: Wall
    2: Check - In Stack
    3: Check - Pass
    4: Road
    10: Start
    20: Goal
    """

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

def a_star(start, goal, grid):
    open_list = []
    closed_list = set()

    start.g = 0
    start.h = manhattan(start, goal)
    start.f = start.g + start.h

    heapq.heappush(open_list, (start.f, start))

    while open_list:
        current = heapq.heappop(open_list)[1]
        if current == goal:
            return reconstruct_path(goal)

        closed_list.add(current)

        for neighbor in get_neighbors(current, grid):
            if neighbor in closed_list:
                continue

            tentative_g = current.g + 1
            if tentative_g < neighbor.g:
                neighbor.parent = current
                neighbor.g = tentative_g
                neighbor.h = manhattan(neighbor, goal)
                neighbor.f = neighbor.g + neighbor.h

                heapq.heappush(open_list, (neighbor.f, neighbor))

def reconstruct_path(goal):
    path = []
    current = goal
    while current.parent:
        path.append(current)
        current = current.parent
    path.reverse()
    return path

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

# A* 알고리즘을 위한 오픈 리스트와 클로즈드 리스트
open_list = []
closed_list = set()

# 메인 루프
running = True
while running:
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
