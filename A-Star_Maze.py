from pico2d import *

class Node:
    """
    state:
    0: Empty
    1: Wall
    2: Check - In Stack
    3: Check - Pass
    10: Start
    20: Goal
    """

    def __init__(self, x=0, y=0, state=0):
        self.x = x
        self.y = y
        self.state = state

# 초기화
open_canvas(800, 600)   # 창 크기 설정 (폭 800, 높이 600)
grid = [[Node(i, j, 0) for j in range(20)] for i in range(20)]

# 메인 루프
running = True
while running:
    clear_canvas()       # 화면 지우기
    update_canvas()      # 화면 갱신

    # 이벤트 처리
    events = get_events()
    for e in events:
        if e.type == SDL_QUIT:     # 창 닫기 버튼 클릭 시 종료
            running = False
        elif e.type == SDL_KEYDOWN and e.key == SDLK_ESCAPE:
            running = False

# 종료
close_canvas()
