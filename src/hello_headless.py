"""
Chương trình kiểm tra môi trường headless cho game Đảo Đèn Lồng (CP0).

Chạy không cần cửa sổ đồ họa. In ra trạng thái ban đầu của game theo định dạng
đơn giản, dùng để Verify môi trường trước khi bắt đầu Phase 1.

Cách chạy:
    python src/hello_headless.py
"""

import json
import sys


def initial_state() -> dict:
    """Trả về trạng thái ban đầu của game (giả lập Test Contract đơn giản)."""
    return {
        "game": "Dao Den Long",
        "phase": "CP0",
        "mode": "headless",
        "player": {
            "name": "Nguoi Giu Den",
            "lantern": False,
            "position": [0, 0, 0],
        },
        "fireflies_collected": 0,
        "lanterns_lit": 0,
        "shadow_squid_encountered": False,
        "status": "ok",
        "message": "Moi truong headless hoat dung tot.",
    }


def main() -> int:
    state = initial_state()
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())