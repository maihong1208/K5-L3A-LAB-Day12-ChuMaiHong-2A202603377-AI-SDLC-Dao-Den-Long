#!/usr/bin/env python3
"""GUI chơi được cho Đảo Đèn Lồng (TICKET-04).

Cài đặt & chạy (3 lệnh):
    pip install -r requirements.txt
    python src/game_gui.py                                  # chơi Đêm 1->2->3
    python src/game_gui.py --export-leaderboard out.json    # xuất bảng xếp hạng

Cửa sổ 1280×720, không toàn màn hình, vsync off. Engine (game_headless) là
source of truth cho luật; GUI chỉ hiển thị + cập nhật state, không đổi đầu ra
headless (Test Contract v1.0–v1.3 giữ nguyên).

Accessibility (TICKET-04 §4): đổi phím + phát hiện trùng + khôi phục mặc định,
phụ đề/chỉ báo hình, giảm chuyển động, cỡ chữ UI (>=18px, chữ lớn x1.25).
Bảng xếp hạng cục bộ (TICKET-04 §3) + --export-leaderboard.
Màu dễ phân biệt (TICKET-03 §6) qua settings.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

from game_headless import Game
from scene_render import Renderer, SKY
import settings_store
import leaderboard

W, H = 1280, 720
NIGHT_ORDER = [1, 2, 3]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ui_size(settings):
    return settings_store.ui_font_size(settings)


def scancode_for(key_name):
    """Tên key -> keycode (index cho pygame.key.get_pressed()).

    Ưu tiên hằng số top-level pygame.K_<NAME> (đã verify K_w, K_LSHIFT, K_SPACE...);
    fallback pygame.key.key_code cho tên dài. 'shift'/'ctrl'/'alt' map K_L*.
    """
    alias = {"shift": "lshift", "ctrl": "lctrl", "alt": "lalt"}
    name = alias.get(key_name, key_name)
    keycode = getattr(pygame, "K_" + name.upper(), None)
    if keycode is None:
        try:
            keycode = pygame.key.key_code(name)
        except Exception:
            keycode = None
    return keycode if keycode is not None else 0


# ---------------------------------------------------------------------------
class LanternGame:
    def __init__(self, settings, seed=42):
        self.settings = settings
        self.renderer = Renderer(W, H)
        self.clock = pygame.time.Clock()
        self.run_seed = seed
        self.total_score = 0
        self.nights_won = 0
        self.night_index = 0
        self._start_night(NIGHT_ORDER[0])

    def _start_night(self, night):
        self.current = Game(self.run_seed + night, night, None)
        self.renderer.cam.follow([0.0, 0.0, 0.0], 0.0)

    def capacity_of(self, g):
        return g._capacity()

    def read_frame(self, keys, edge):
        g = self.current
        kb = self.settings["keybinds"]

        def pressed(name):
            sc = scancode_for(kb[name])
            return keys[sc] if sc < len(keys) else False

        move = [0.0, 0.0]
        if pressed("up"):
            move[1] += 1
        if pressed("down"):
            move[1] -= 1
        if pressed("left"):
            move[0] -= 1
        if pressed("right"):
            move[0] += 1
        import math
        frame = {"move": move, "cam_yaw_deg": 0.0}
        for act in ("jump", "dash", "pulse", "interact"):
            if edge.get(act):
                frame[act] = True
        return frame

    def step(self, frame, edge):
        g = self.current
        g.apply_input(frame)
        g.step()
        if g.state != "playing":
            won = g.state == "won"
            self.total_score += g.score
            if won:
                self.nights_won += 1
            if won and self.night_index < len(NIGHT_ORDER) - 1:
                self.night_index += 1
                self._start_night(NIGHT_ORDER[self.night_index])
                return "next"
            return "end"
        return "playing"


# ---------------------------------------------------------------------------
def run_gui(settings):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Đảo Đèn Lồng")
    game = LanternGame(settings)

    running = True
    ended = False
    f_main = None
    f_small = None
    subtitle_buf = []

    while running:
        g = game.current
        dtms = game.clock.tick(0)  # vsync off
        f_main = f_main or pygame.font.SysFont(None, ui_size(settings))
        f_small = f_small or pygame.font.SysFont(None, max(14, ui_size(settings) - 4))

        edge = {}
        keys = pygame.key.get_pressed()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
                break
            if ev.type == pygame.KEYDOWN:
                nm = pygame.key.get_scancode_name(ev.scancode)
                if nm == "escape":
                    running = False
                    break
                # So sánh keycode (ev.key), không phải scancode, để khớp get_pressed.
                for act, key in settings["keybinds"].items():
                    if act in ("jump", "dash", "pulse", "interact") and \
                            scancode_for(key) == ev.key:
                        edge[act] = True
                # toggle tạm dừng (giữ nguyên luật, chỉ dừng UI)
                if scancode_for(settings["keybinds"]["pause"]) == ev.key:
                    pygame.time.wait(600)
                    continue

        frame = game.read_frame(keys, edge)
        status = game.step(frame, edge)
        if status == "next":
            subtitle_buf.append(("Đêm kế tiếp bắt đầu.", 2000))
        elif status == "end":
            ended = True
            break

        game.renderer.cam.follow([g.player_pos[0], g.player_pos[1], g.player_pos[2]],
                                 game.current.player_yaw)

        screen.fill(SKY)
        game.renderer.render(screen, g, settings_store.palette(settings),
                             reduce_motion=settings.get("reduce_motion", False))
        _draw_hud(screen, g, game, settings, f_main, f_small, subtitle_buf)
        pygame.display.flip()

        for i in range(len(subtitle_buf)):
            subtitle_buf[i] = (subtitle_buf[i][0], subtitle_buf[i][1] - dtms)
        subtitle_buf[:] = [x for x in subtitle_buf if x[1] > 0]

    if ended:
        ok, name = name_entry_dialog(screen, game.total_score, game.nights_won, settings)
        if ok:
            try:
                leaderboard.add_entry(name, game.total_score, game.nights_won, game.run_seed)
            except leaderboard.LeaderboardError as e:
                print(f"Không lưu điểm: {e}", file=sys.stderr)
        show_leaderboard_screen(screen, settings)

    pygame.quit()
    return 0


def _draw_hud(screen, g, game, settings, f_main, f_small, subtitle_buf):
    pal = settings_store.palette(settings)
    t = int(max(0, g.time_left))
    line = (f"Đêm {g.night}  ·  {t}s  ·  Ngọn lửa {g.player_flames}  ·  "
            f"Mang {g.player_carried}/{game.capacity_of(g)}  ·  Điểm {g.score}")
    screen.blit(f_main.render(line, True, (255, 255, 255)), (12, 12))
    if t <= 10 and g.state == "playing":
        screen.blit(f_small.render("10 GIÂY CUỐI — giữ đảo sáng tới bình minh!", True,
                                   hex_to_rgb(pal["warning"])), (12, 40))
    weak = [L["id"] for L in g.lanterns if L["lit"] and L["fuel_60"] < 1800]
    if weak and settings.get("subtitles", True):
        screen.blit(f_small.render("Đèn yếu (<30): " + ", ".join(weak), True,
                                   hex_to_rgb(pal["warning"])), (12, 64))
    if settings.get("subtitles", True):
        for text, _ttl in subtitle_buf:
            screen.blit(f_small.render(text, True, (255, 255, 255)), (12, 88))


def name_entry_dialog(screen, score, nights_won, settings):
    pygame.font.init()
    f = pygame.font.SysFont(None, ui_size(settings))
    name = ""
    while True:
        screen.fill((18, 18, 30))
        screen.blit(f.render(f"Bình minh! Tổng điểm: {score} · Đêm thắng: {nights_won}",
                             True, (255, 255, 255)), (60, 60))
        screen.blit(f.render("Nhập tên (3–12: chữ/số/_) rồi ENTER · ESC bỏ qua:",
                             True, (200, 200, 220)), (60, 110))
        box = pygame.Rect(60, 160, 340, 44)
        pygame.draw.rect(screen, (60, 60, 84), box)
        screen.blit(f.render(name + ("|" if False else ""), True, (255, 255, 255)), (68, 170))
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return (False, None)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return (False, None)
                if ev.key == pygame.K_RETURN:
                    if leaderboard.name_is_valid(name):
                        return (True, name)
                elif ev.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif ev.unicode and len(name) < 12 and (ev.unicode.isalnum() or ev.unicode == "_"):
                    name += ev.unicode
        pygame.display.flip()
        pygame.time.wait(20)


def show_leaderboard_screen(screen, settings):
    f = pygame.font.SysFont(None, ui_size(settings))
    screen.fill((14, 16, 28))
    screen.blit(f.render("Bảng xếp hạng (top 10)", True, (255, 210, 120)), (60, 50))
    entries = leaderboard.export()["entries"]
    header = f"{'#':<3}{'Tên':<14}{'Điểm':>8}{'Đêm thắng':>14}{'Thời điểm':>24}{'Seed':>7}"
    screen.blit(f.render(header, True, (180, 180, 200)), (60, 100))
    for i, e in enumerate(entries, 1):
        row = (f"{i:<3}{e['name']:<14}{e['score']:>8}{e['nights_won']:>14}"
               f"{e['achieved_at']:>24}{e['seed']:>7}")
        screen.blit(f.render(row, True, (220, 220, 235)), (60, 140 + i * 32))
    if not entries:
        screen.blit(f.render("(chưa có điểm nào)", True, (140, 140, 150)), (60, 140))
    screen.blit(f.render("Nhấn bất kỳ phím nào để thoát.", True, (140, 140, 150)), (60, 480))
    pygame.display.flip()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.KEYDOWN:
                return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-leaderboard", metavar="OUT.json",
                    help="Xuất bảng xếp hạng rồi thoát (TICKET-04 §3).")
    args = ap.parse_args()

    if args.export_leaderboard:
        data = leaderboard.export()
        with open(args.export_leaderboard, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    settings = settings_store.load_settings()
    return run_gui(settings)


if __name__ == "__main__":
    sys.exit(main())
