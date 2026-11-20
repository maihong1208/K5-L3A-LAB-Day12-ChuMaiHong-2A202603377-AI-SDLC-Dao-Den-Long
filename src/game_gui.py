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
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

from game_headless import Game
from scene_render import Renderer, SKY
import settings_store
import leaderboard

W, H = 1280, 720
FPS_CAP = 60
NIGHT_ORDER = [1, 2, 3]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ui_size(settings):
    return settings_store.ui_font_size(settings)


def scancode_for(key_name):
    """Tên key -> keycode (index cho pygame.key.get_pressed()).

    Dùng các hằng số pygame viết thường cho phím chữ và hằng số viết hoa cho
    phím đặc biệt; fallback qua key_code cho các tên hợp lệ khác.
    """
    alias = {
        "shift": "lshift", "left shift": "lshift", "right shift": "rshift",
        "ctrl": "lctrl", "left ctrl": "lctrl", "right ctrl": "rctrl",
        "alt": "lalt", "left alt": "lalt", "right alt": "ralt",
    }
    name = alias.get(key_name, key_name)
    keycode = getattr(pygame, "K_" + name, None)
    if keycode is None:
        keycode = getattr(pygame, "K_" + name.upper(), None)
    if keycode is None:
        try:
            keycode = pygame.key.key_code(name)
        except ValueError:
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
        frame = {"move": move, "cam_yaw_deg": 0.0}
        for act in ("jump", "dash", "pulse", "interact", "pause"):
            frame[act] = bool(edge.get(act))
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
def _font(size, bold=False):
    return pygame.font.SysFont("segoeui", size, bold=bold)


def _draw_panel(screen, rect, fill=(11, 18, 32, 220), border=(134, 160, 177)):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill(fill)
    screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=16)


def _draw_backdrop(screen, renderer, world, settings, started_at):
    elapsed = (pygame.time.get_ticks() - started_at) / 1000.0
    angle = 0.35 if settings.get("reduce_motion") else elapsed * 0.12 + 0.35
    renderer.cam.set_orbit(47.0, 25.0, angle, [0.0, 0.0, 0.0])
    renderer.render(screen, world, settings_store.palette(settings),
                    reduce_motion=settings.get("reduce_motion", False))
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    shade.fill((5, 10, 25, 155))
    screen.blit(shade, (0, 0))


def _button(screen, rect, text, font, selected=False, hovered=False):
    active = selected or hovered
    fill = (201, 140, 62, 245) if active else (30, 43, 58, 232)
    border = (255, 219, 152) if active else (88, 112, 132)
    _draw_panel(screen, rect, fill, border)
    label = font.render(text, True, (255, 249, 232) if active else (222, 231, 236))
    screen.blit(label, label.get_rect(midleft=(rect.x + 22, rect.centery)))


def main_menu(screen, settings, renderer, world):
    options = [
        ("Bắt đầu hành trình", "play"),
        ("Cài đặt & trợ năng", "settings"),
        ("Bảng xếp hạng", "leaderboard"),
        ("Thoát", "quit"),
    ]
    selected = 0
    button_font = _font(max(20, ui_size(settings)), True)
    title_font = _font(54, True)
    sub_font = _font(20)
    clock = pygame.time.Clock()
    started_at = pygame.time.get_ticks()
    rects = [pygame.Rect(78, 268 + i * 78, 430, 62) for i in range(len(options))]

    while True:
        clock.tick(FPS_CAP)
        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(rects):
            if rect.collidepoint(mouse):
                selected = i
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return options[selected][1]
                elif ev.key == pygame.K_ESCAPE:
                    return "quit"
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, rect in enumerate(rects):
                    if rect.collidepoint(ev.pos):
                        return options[i][1]

        _draw_backdrop(screen, renderer, world, settings, started_at)
        _draw_panel(screen, pygame.Rect(50, 42, 1180, 122), (9, 15, 30, 205))
        title = title_font.render("ĐẢO ĐÈN LỒNG", True, (255, 220, 160))
        screen.blit(title, title.get_rect(center=(W // 2, 91)))
        subtitle = sub_font.render("Một đêm dài. Năm ngọn đèn. Đừng để ánh sáng tắt.", True,
                                   (224, 232, 236))
        screen.blit(subtitle, subtitle.get_rect(center=(W // 2, 135)))

        _draw_panel(screen, pygame.Rect(50, 205, 488, 410))
        for i, ((label, _action), rect) in enumerate(zip(options, rects)):
            _button(screen, rect, label, button_font, selected=i == selected,
                    hovered=rect.collidepoint(mouse))

        _draw_panel(screen, pygame.Rect(570, 205, 660, 410))
        headings = _font(25, True).render("MỤC TIÊU ĐÊM NAY", True, (255, 220, 160))
        screen.blit(headings, (602, 236))
        binds = settings["keybinds"]
        lines = [
            "Thu thập đom đóm rồi mang đến Đèn Lồng Lớn.",
            "Giữ ít nhất 60% số đèn sáng đến bình minh.",
            "Bóng Mực sẽ đuổi theo — dùng Tỏa Sáng để xua chúng.",
            "",
            f"{binds['up'].upper()}/{binds['left'].upper()}/{binds['down'].upper()}/{binds['right'].upper()}  Di chuyển",
            f"{binds['interact'].upper()}  Thắp/nạp    {binds['pulse'].upper()}  Tỏa sáng    {binds['jump'].upper()}  Nhảy",
            f"{binds['dash'].upper()}  Lướt    {binds['pause'].upper()}  Tạm dừng",
            "",
            "Mây sẽ đi qua ba đêm; mỗi đêm cần thêm ánh sáng.",
        ]
        line_font = _font(19)
        for i, text in enumerate(lines):
            color = (226, 234, 239) if text else (226, 234, 239)
            screen.blit(line_font.render(text, True, color), (603, 285 + i * 30))
        pygame.display.flip()


def settings_screen(screen, settings, renderer, world):
    toggles = [
        ("Bảng màu dễ phân biệt", "colorblind_mode"),
        ("Phụ đề và chỉ báo", "subtitles"),
        ("Giảm chuyển động", "reduce_motion"),
        ("Chữ lớn (×1.25)", "large_text"),
    ]
    actions = [
        ("Di chuyển lên", "up"), ("Di chuyển xuống", "down"),
        ("Di chuyển trái", "left"), ("Di chuyển phải", "right"),
        ("Nhảy", "jump"), ("Lướt", "dash"), ("Tương tác", "interact"),
        ("Tỏa sáng", "pulse"), ("Tạm dừng", "pause"),
    ]
    labels = [label for label, _ in toggles] + [label for label, _ in actions] + [
        "Khôi phục phím mặc định", "Quay lại",
    ]
    selected = 0
    capture_action = None
    clock = pygame.time.Clock()
    started_at = pygame.time.get_ticks()
    font = _font(max(18, ui_size(settings) - 1))
    title_font = _font(34, True)
    row_rects = [pygame.Rect(160, 132 + i * 32, 960, 31) for i in range(len(labels))]
    toggle_count = len(toggles)
    reset_index = toggle_count + len(actions)
    back_index = reset_index + 1

    def finish():
        settings_store.save_settings(settings=settings)
        return "back"

    while True:
        clock.tick(FPS_CAP)
        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(row_rects):
            if rect.collidepoint(mouse):
                selected = i
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                settings_store.save_settings(settings=settings)
                return "quit"
            if ev.type == pygame.KEYDOWN:
                if capture_action is not None:
                    if ev.key == pygame.K_ESCAPE:
                        capture_action = None
                    else:
                        key_name = pygame.key.name(ev.key).lower()
                        if key_name and key_name != "unknown":
                            aliases = {
                                "left shift": "shift", "right shift": "shift",
                                "left ctrl": "ctrl", "right ctrl": "ctrl",
                                "left alt": "alt", "right alt": "alt",
                            }
                            settings["keybinds"][capture_action] = aliases.get(key_name, key_name)
                            capture_action = None
                    continue
                if ev.key == pygame.K_ESCAPE:
                    return finish()
                if ev.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(labels)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(labels)
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected < toggle_count:
                        key = toggles[selected][1]
                        settings[key] = not settings.get(key, False)
                    elif selected < reset_index:
                        capture_action = actions[selected - toggle_count][1]
                    elif selected == reset_index:
                        settings["keybinds"] = dict(settings_store.DEFAULT_KEYBINDS)
                    else:
                        return finish()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, rect in enumerate(row_rects):
                    if rect.collidepoint(ev.pos):
                        selected = i
                        if i < toggle_count:
                            key = toggles[i][1]
                            settings[key] = not settings.get(key, False)
                        elif i < reset_index:
                            capture_action = actions[i - toggle_count][1]
                        elif i == reset_index:
                            settings["keybinds"] = dict(settings_store.DEFAULT_KEYBINDS)
                        else:
                            return finish()

        _draw_backdrop(screen, renderer, world, settings, started_at)
        _draw_panel(screen, pygame.Rect(125, 48, 1030, 610), (9, 15, 30, 236))
        screen.blit(title_font.render("CÀI ĐẶT & TRỢ NĂNG", True, (255, 220, 160)), (165, 76))
        for i, (label, rect) in enumerate(zip(labels, row_rects)):
            if i == selected:
                pygame.draw.rect(screen, (73, 91, 104), rect, border_radius=6)
            if i < toggle_count:
                value = "BẬT" if settings.get(toggles[i][1], False) else "TẮT"
                value_color = (154, 227, 181) if value == "BẬT" else (196, 205, 212)
                screen.blit(font.render(label, True, (235, 239, 240)), (rect.x + 12, rect.y + 3))
                value_surface = font.render(value, True, value_color)
                screen.blit(value_surface, (rect.right - value_surface.get_width() - 15, rect.y + 3))
            elif i < reset_index:
                action = actions[i - toggle_count][1]
                if capture_action == action:
                    binding = "NHẤN PHÍM MỚI · Esc hủy"
                    color = (255, 220, 160)
                else:
                    binding = settings["keybinds"].get(action, "?").upper()
                    color = (221, 231, 236)
                screen.blit(font.render(label, True, (235, 239, 240)), (rect.x + 12, rect.y + 3))
                binding_surface = font.render(binding, True, color)
                screen.blit(binding_surface, (rect.right - binding_surface.get_width() - 15, rect.y + 3))
            else:
                screen.blit(font.render(label, True, (255, 220, 160)), (rect.x + 12, rect.y + 3))

        conflicts = settings_store.key_conflicts(settings)
        if conflicts:
            msg = "Trùng phím: " + "; ".join(" / ".join(items) for items in conflicts)
            screen.blit(font.render(msg, True, (255, 110, 110)), (165, 612))
        else:
            screen.blit(font.render("Phím không bị trùng. Enter chọn · Esc quay lại", True,
                                    (174, 193, 205)), (165, 612))
        pygame.display.flip()


def show_leaderboard_screen(screen, settings):
    entries = leaderboard.export()["entries"]
    clock = pygame.time.Clock()
    title_font = _font(34, True)
    font = _font(max(18, ui_size(settings)))
    small = _font(18)
    while True:
        clock.tick(30)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "quit"
            if ev.type == pygame.KEYDOWN or (
                    ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1):
                return "back"

        screen.fill((10, 17, 30))
        _draw_panel(screen, pygame.Rect(120, 55, 1040, 610), (18, 28, 43, 245))
        title = title_font.render("BẢNG XẾP HẠNG", True, (255, 220, 160))
        screen.blit(title, title.get_rect(center=(W // 2, 100)))
        headers = ("#", "Tên", "Điểm", "Đêm thắng", "Đạt lúc", "Seed")
        x = (170, 230, 430, 570, 745, 1050)
        for label, px in zip(headers, x):
            screen.blit(font.render(label, True, (153, 188, 198)), (px, 158))
        if not entries:
            empty = font.render("Chưa có điểm nào — hãy bắt đầu hành trình!", True, (224, 232, 236))
            screen.blit(empty, empty.get_rect(center=(W // 2, 260)))
        for i, entry in enumerate(entries[:10], 1):
            y = 202 + (i - 1) * 38
            color = (255, 220, 160) if i == 1 else (224, 232, 236)
            values = (
                str(i), entry["name"], str(entry["score"]), str(entry["nights_won"]),
                entry["achieved_at"].replace("T", " ")[:19], str(entry["seed"]),
            )
            for value, px in zip(values, x):
                screen.blit(font.render(value, True, color), (px, y))
        hint = small.render("Enter hoặc Esc để quay lại", True, (164, 184, 197))
        screen.blit(hint, hint.get_rect(center=(W // 2, 610)))
        pygame.display.flip()


def _resume_engine(game):
    g = game.current
    if not g.paused:
        return
    g.apply_input({"move": [0.0, 0.0], "pause": False})
    g.step()
    g.apply_input({"move": [0.0, 0.0], "pause": True})
    g.step()
    g.apply_input({"pause": False})


def pause_menu(screen, game, settings, fonts):
    options = ["Tiếp tục", "Cài đặt & trợ năng", "Về màn hình chính", "Thoát"]
    selected = 0
    clock = pygame.time.Clock()
    rects = [pygame.Rect(405, 285 + i * 66, 470, 52) for i in range(len(options))]
    while True:
        clock.tick(30)
        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(rects):
            if rect.collidepoint(mouse):
                selected = i
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif ev.key in (
                        pygame.K_ESCAPE, scancode_for(settings["keybinds"]["pause"])):
                    return "resume"
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected == 0:
                        return "resume"
                    if selected == 1:
                        outcome = settings_screen(screen, settings, game.renderer, game.current)
                        if outcome == "quit":
                            return "quit"
                    elif selected == 2:
                        return "menu"
                    else:
                        return "quit"
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, rect in enumerate(rects):
                    if rect.collidepoint(ev.pos):
                        if i == 0:
                            return "resume"
                        if i == 1:
                            outcome = settings_screen(screen, settings, game.renderer, game.current)
                            if outcome == "quit":
                                return "quit"
                        elif i == 2:
                            return "menu"
                        else:
                            return "quit"

        g = game.current
        game.renderer.cam.follow(g.player_pos, g.player_yaw)
        game.renderer.render(screen, g, settings_store.palette(settings),
                             reduce_motion=settings.get("reduce_motion", False))
        _draw_hud(screen, g, game, settings, *fonts, [])
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((4, 8, 18, 190))
        screen.blit(overlay, (0, 0))
        _draw_panel(screen, pygame.Rect(345, 190, 590, 420), (13, 21, 36, 245))
        title = _font(38, True).render("TẠM DỪNG", True, (255, 220, 160))
        screen.blit(title, title.get_rect(center=(W // 2, 235)))
        for i, (label, rect) in enumerate(zip(options, rects)):
            _button(screen, rect, label, fonts[0], selected=i == selected,
                    hovered=rect.collidepoint(mouse))
        pygame.display.flip()


def play_game(screen, game, settings):
    font_main = _font(ui_size(settings), True)
    font_small = _font(max(18, ui_size(settings) - 1))
    subtitle_buf = []
    while True:
        dtms = game.clock.tick(FPS_CAP)
        g = game.current
        edge = {}
        keys = pygame.key.get_pressed()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    edge["pause"] = True
                    continue
                for action, bound_key in settings["keybinds"].items():
                    if action in ("jump", "dash", "pulse", "interact", "pause") and \
                            scancode_for(bound_key) == ev.key:
                        edge[action] = True

        frame = game.read_frame(keys, edge)
        status = game.step(frame, edge)
        if status == "end":
            return "end"
        if status == "next":
            subtitle_buf.append(("Đêm kế tiếp bắt đầu.", 2000))
            g = game.current

        game.renderer.cam.follow(g.player_pos, g.player_yaw)
        game.renderer.render(screen, g, settings_store.palette(settings),
                             reduce_motion=settings.get("reduce_motion", False))
        _draw_hud(screen, g, game, settings, font_main, font_small, subtitle_buf)
        pygame.display.flip()

        for i, (text, ttl) in enumerate(subtitle_buf):
            subtitle_buf[i] = (text, ttl - dtms)
        subtitle_buf[:] = [item for item in subtitle_buf if item[1] > 0]

        if g.paused:
            action = pause_menu(screen, game, settings, (font_main, font_small))
            if action == "quit":
                return "quit"
            _resume_engine(game)
            if action == "menu":
                return "menu"


def _draw_hud(screen, g, game, settings, f_main, f_small, subtitle_buf):
    palette = settings_store.palette(settings)
    timer = int(max(0, g.time_left))
    lit = sum(1 for lantern in g.lanterns if lantern["lit"])
    need = int(math.ceil(0.6 * len(g.lanterns)))
    total_score = game.total_score + g.score
    panel = pygame.Surface((475, 144), pygame.SRCALPHA)
    panel.fill((8, 15, 28, 210))
    screen.blit(panel, (12, 12))
    pygame.draw.rect(screen, (132, 155, 171), (12, 12, 475, 144), 1, border_radius=12)
    line = f"ĐÊM {g.night}   {timer // 60:02d}:{timer % 60:02d}   ĐIỂM {total_score}"
    screen.blit(f_main.render(line, True, (255, 231, 187)), (27, 21))
    details = (
        f"Đèn sáng: {lit}/{len(g.lanterns)}  (cần {need})",
        f"Đom đóm: {g.player_carried}/{game.capacity_of(g)}",
        f"Ngọn lửa: {g.player_flames}",
    )
    for i, text in enumerate(details):
        screen.blit(f_small.render(text, True, (229, 236, 240)), (27, 54 + i * 25))

    if settings.get("subtitles", True):
        objective = f"Giữ ≥{need} đèn sáng tới bình minh"
        screen.blit(f_small.render(objective, True, (255, 220, 160)), (510, 22))
        weak = [lantern["id"] for lantern in g.lanterns
                if lantern["lit"] and lantern["fuel_60"] < 1800]
        if weak:
            warning_color = hex_to_rgb(palette["warning"])
            pygame.draw.polygon(screen, warning_color, ((518, 50), (508, 68), (528, 68)))
            pygame.draw.line(screen, (24, 28, 38), (518, 55), (518, 62), 2)
            pygame.draw.circle(screen, (24, 28, 38), (518, 65), 1)
            screen.blit(f_small.render("Đèn yếu: " + ", ".join(weak), True,
                                       warning_color), (536, 49))
        if g.wind_active:
            screen.blit(f_small.render("Gió đang thổi", True, (190, 220, 255)), (510, 80))
        elif 0 < g.wind_next_ticks <= 600:
            warning = f"Gió sắp thổi sau {math.ceil(g.wind_next_ticks / 60)}s"
            screen.blit(f_small.render(warning, True, hex_to_rgb(palette["warning"])), (510, 80))
        if timer <= 10 and g.state == "playing":
            screen.blit(f_small.render("10 GIÂY CUỐI — giữ đảo sáng!", True,
                                       hex_to_rgb(palette["warning"])), (510, 109))
        if subtitle_buf:
            screen.blit(f_small.render(subtitle_buf[-1][0], True, (255, 255, 255)), (510, 138))

        if g.shades:
            nearest = min(g.shades, key=lambda shade: math.hypot(
                shade["pos"][0] - g.player_pos[0], shade["pos"][2] - g.player_pos[2]))
            dx = nearest["pos"][0] - g.player_pos[0]
            dz = nearest["pos"][2] - g.player_pos[2]
            distance = math.hypot(dx, dz)
            angle = math.atan2(dx, dz)
            direction = (math.sin(angle), -math.cos(angle))
            perpendicular = (direction[1], -direction[0])
            center = (W // 2 + int(direction[0] * 560), H // 2 + int(direction[1] * 275))
            tip = (center[0] + int(direction[0] * 18), center[1] + int(direction[1] * 18))
            left = (center[0] - int(direction[0] * 12) + int(perpendicular[0] * 10),
                    center[1] - int(direction[1] * 12) + int(perpendicular[1] * 10))
            right = (center[0] - int(direction[0] * 12) - int(perpendicular[0] * 10),
                     center[1] - int(direction[1] * 12) - int(perpendicular[1] * 10))
            pygame.draw.polygon(screen, hex_to_rgb(palette["shade_outline"]), (tip, left, right))
            label = f"Bóng Mực · {distance:.0f}m"
            badge = f_small.render(label, True, (244, 238, 255))
            screen.blit(badge, (W - badge.get_width() - 18, 18))

    binds = settings["keybinds"]
    help_text = (
        f"{binds['up'].upper()}/{binds['left'].upper()}/{binds['down'].upper()}/"
        f"{binds['right'].upper()} di chuyển · {binds['interact'].upper()} thắp/nạp · "
        f"{binds['pulse'].upper()} tỏa sáng · {binds['jump'].upper()} nhảy · "
        f"{binds['dash'].upper()} lướt · {binds['pause'].upper()} tạm dừng"
    )
    footer = pygame.Surface((W, 36), pygame.SRCALPHA)
    footer.fill((8, 15, 28, 215))
    screen.blit(footer, (0, H - 36))
    help_surface = f_small.render(help_text, True, (220, 230, 235))
    screen.blit(help_surface, help_surface.get_rect(center=(W // 2, H - 18)))


def run_gui(settings):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Đảo Đèn Lồng")
    menu_renderer = Renderer(W, H)
    menu_world = Game(42, 1)

    while True:
        choice = main_menu(screen, settings, menu_renderer, menu_world)
        if choice == "quit":
            break
        if choice == "settings":
            if settings_screen(screen, settings, menu_renderer, menu_world) == "quit":
                break
            continue
        if choice == "leaderboard":
            if show_leaderboard_screen(screen, settings) == "quit":
                break
            continue

        game = LanternGame(settings)
        result = play_game(screen, game, settings)
        if result == "quit":
            break
        if result == "menu":
            continue

        accepted, name = name_entry_dialog(
            screen, game.total_score, game.nights_won, settings, game.current.state)
        if accepted:
            try:
                leaderboard.add_entry(
                    name, game.total_score, game.nights_won, game.run_seed)
            except leaderboard.LeaderboardError as error:
                print(f"Không lưu điểm: {error}", file=sys.stderr)
        if show_leaderboard_screen(screen, settings) == "quit":
            break

    settings_store.save_settings(settings=settings)
    pygame.quit()
    return 0


def name_entry_dialog(screen, score, nights_won, settings, result_state="won"):
    clock = pygame.time.Clock()
    title_font = _font(34, True)
    f = _font(max(18, ui_size(settings)))
    small = _font(18)
    name = ""
    while True:
        clock.tick(30)
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
        screen.fill((9, 15, 29))
        _draw_panel(screen, pygame.Rect(240, 160, 800, 390), (17, 27, 42, 245))
        title_text = "BÌNH MINH" if result_state == "won" else "ĐÊM KẾT THÚC"
        title = title_font.render(title_text, True, (255, 220, 160))
        screen.blit(title, title.get_rect(center=(W // 2, 220)))
        summary = f.render(f"Tổng điểm: {score}     Đêm thắng: {nights_won}/3",
                           True, (228, 236, 240))
        screen.blit(summary, summary.get_rect(center=(W // 2, 285)))
        screen.blit(f.render("Nhập tên vào bảng xếp hạng", True, (228, 236, 240)),
                    (355, 345))
        box = pygame.Rect(355, 385, 570, 56)
        pygame.draw.rect(screen, (29, 43, 58), box, border_radius=8)
        pygame.draw.rect(screen, (255, 220, 160), box, width=2, border_radius=8)
        cursor = "" if settings.get("reduce_motion") or pygame.time.get_ticks() % 1000 < 500 else " "
        screen.blit(f.render(name + cursor, True, (255, 255, 255)), (370, 397))
        hint = "3–12 ký tự [A-Za-z0-9_] · Enter lưu · Esc bỏ qua"
        screen.blit(small.render(hint, True, (170, 190, 202)), (355, 468))
        pygame.display.flip()


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
