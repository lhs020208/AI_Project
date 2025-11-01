from pico2d import *

# 초기화
open_canvas(800, 600)   # 창 크기 설정 (폭 800, 높이 600)

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
