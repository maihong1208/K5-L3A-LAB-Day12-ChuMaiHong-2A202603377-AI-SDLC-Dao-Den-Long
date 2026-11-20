"""Cài đặt người chơi (Ticket-04 §4 accessibility + §6 Phase 3 màu dễ phân biệt).

LƯU trên đĩa cục bộ (config/settings.json) nên còn sau khi tắt/mở lại.
Tất cả chỉ là tuỳ chọn HIỂN THỊ / ĐIỀU KHIỂN; không đổi luật game hay
đầu ra headless (Test Contract vẫn giữ nguyên) để mọi bài đo trên cùng cảnh chuẩn.

Khả năng truy cập (accessibility) theo TICKET-04 §4:
- Đổi phím mọi hành động + phát hiện trùng phím + nút khôi phục mặc định.
- Phụ đề / chỉ báo hình (Bóng Mực, gió, 10s cuối, đèn yếu).
- Giảm chuyển động (tắt rung camera + chớp màn hình).
- Cỡ chữ UI (mặc định >= 18px @1280x720; tuỳ chọn chữ lớn x1.25).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_PATH = ROOT / "config" / "settings.json"

# Hành động bắt buộc phải có thể đổi phím (TICKET-04 §4).
ACTIONS = ["up", "down", "left", "right", "jump", "dash", "interact", "pulse", "pause"]
DEFAULT_KEYBINDS = {
    "up": "w", "down": "s", "left": "a", "right": "d",
    "jump": "space", "dash": "shift", "interact": "e",
    "pulse": "q", "pause": "p",
}
PALETTE_DEFAULT = {"shade_outline": "#7A3CFF", "warning": "#FF5A5F"}
PALETTE_COLORBLIND = {"shade_outline": "#00B3FF", "warning": "#FFFFFF"}
MIN_UI_FONT_PX = 18          # @1280x720 (TICKET-04 §4)
LARGE_TEXT_SCALE = 1.25


def _defaults() -> dict:
    return {
        "colorblind_mode": False,
        "reduce_motion": False,
        "subtitles": True,
        "large_text": False,
        "keybinds": dict(DEFAULT_KEYBINDS),
    }


def load_settings(path=DEFAULT_SETTINGS_PATH) -> dict:
    s = _defaults()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in s:
                if k in data:
                    s[k] = data[k]
            # keybinds: gộp từng hành động (tránh thiếu key khi file cũ).
            merged = dict(DEFAULT_KEYBINDS)
            kb = data.get("keybinds")
            if isinstance(kb, dict):
                for k in ACTIONS:
                    if k in kb:
                        merged[k] = kb[k]
            s["keybinds"] = merged
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return s


def save_settings(path=DEFAULT_SETTINGS_PATH, settings=None) -> dict:
    s = load_settings(path) if settings is None else settings
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    return s


def reset_keybinds(settings: dict, path=DEFAULT_SETTINGS_PATH) -> dict:
    """Nút 'Khôi phục mặc định' (TICKET-04 §4)."""
    settings["keybinds"] = dict(DEFAULT_KEYBINDS)
    save_settings(path, settings)
    return settings


def key_conflicts(settings: dict) -> list:
    """Trả về danh sách key bị gán cho >= 2 hành động (trùng phím)."""
    kb = settings.get("keybinds", {})
    seen = {}
    conflicts = []
    for action, key in kb.items():
        seen.setdefault(key, []).append(action)
    for key, acts in seen.items():
        if len(acts) > 1:
            conflicts.append(sorted(acts))
    return conflicts


def ui_font_size(settings: dict) -> int:
    base = MIN_UI_FONT_PX
    if settings.get("large_text"):
        base = int(base * LARGE_TEXT_SCALE)
    return base


def palette(settings: dict) -> dict:
    return PALETTE_COLORBLIND if settings.get("colorblind_mode") else PALETTE_DEFAULT
