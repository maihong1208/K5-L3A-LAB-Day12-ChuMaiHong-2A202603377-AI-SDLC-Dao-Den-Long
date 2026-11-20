"""Bảng xếp hạng cục bộ (TICKET-04 §3).

- Tên: 3–12 ký tự [A-Za-z0-9_] (tiếng Việt có dấu là điểm cộng, không bắt buộc).
- Mỗi mục: name, score (tổng điểm các Đêm đã thắng), nights_won (0–3),
  achieved_at (ISO 8601 có múi giờ), seed.
- Giữ top 10; sắp xếp score giảm, bằng điểm thì ai đạt trước đứng trên.
- Lưu trên đĩa (data/leaderboard.json), còn sau khi tắt/mở lại game.
- Xuất: `python src/game_gui.py --export-leaderboard out.json`
  -> {"entries": [ ... ]} đúng thứ tự.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "leaderboard.json"

_NAME_RE = re.compile(r"^[A-Za-z0-9_]{3,12}$")
TOP_N = 10
VALID_NIGHTS_WON = (0, 1, 2, 3)


class LeaderboardError(ValueError):
    pass


def name_is_valid(name) -> bool:
    if not isinstance(name, str):
        return False
    return bool(_NAME_RE.match(name))


def _load(path=DEFAULT_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", []) if isinstance(data, dict) else []
        return entries
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(entries, path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, indent=2, ensure_ascii=False)


def _rank_key(e):
    # score giảm; bằng điểm -> achieved_at sớm hơn đứng trên.
    return (-int(e["score"]), str(e["achieved_at"]))


def add_entry(name, score, nights_won, seed, path=DEFAULT_PATH, when=None):
    """Thêm 1 mục hợp lệ; trả về list top 10 đã sắp xếp (lưu đĩa)."""
    if not name_is_valid(name):
        raise LeaderboardError(
            f"Tên không hợp lệ: '{name}' (cần 3–12 ký tự [A-Za-z0-9_]).")
    if nights_won not in VALID_NIGHTS_WON:
        raise LeaderboardError(f"nights_won phải là 0–3, nhận được {nights_won}.")
    if when is None:
        when = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    entry = {
        "name": name,
        "score": int(score),
        "nights_won": int(nights_won),
        "achieved_at": when,
        "seed": seed,
    }
    entries = _load(path) + [entry]
    entries.sort(key=_rank_key)
    top = entries[:TOP_N]
    _save(top, path)
    return top


def export(path=DEFAULT_PATH):
    """Trả về {'entries': [...]} đúng thứ tự, dùng cho --export-leaderboard."""
    return {"entries": _load(path)}


def reset(path=DEFAULT_PATH):
    _save([], path)
    return {"entries": []}
