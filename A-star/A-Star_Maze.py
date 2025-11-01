from pico2d import *

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

    # 이벤트 처리
    for e in get_events():
        if e.type == SDL_QUIT or (e.type == SDL_KEYDOWN and e.key == SDLK_ESCAPE):
            running = False

close_canvas()
