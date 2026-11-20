# Giả định Phase 1 (PRD-0)

## Môi trường
- Ngôn ngữ: Python 3 (chạy được trên macOS/Linux/Windows, không ràng buộc công nghệ theo PRD-0).
- Chế độ headless: `src/game_headless.py` chạy không cửa sổ, xuất JSONL theo Test Contract v1.0.
- Lệnh chạy headless: `python src/game_headless.py --seed <int> --night 1 --ticks <int> --out <file.jsonl>`

## Game (dựa trên PRD-0)
- Một màn: Đêm 1 – Đảo Bến, đảo tròn, 5 Đèn Lồng Lớn (L1..L5).
- Người chơi: Mây, người giữ đèn, xuất phát tại (0,0,0).
- Đom đóm xuất hiện rải rác, nhặt được bằng interact trong pickup_radius.
- Nạp ánh sáng vào đèn bằng interact trong interact_radius; mỗi đèn cần 1 đom đóm để thắp.
- Bóng Mực đuổi người chơi, sợ đèn đã thắp (safe_radius), tát máu khi chạm (shade_hit_radius).
- Tỏa sáng (pulse) xua Bóng Mực trong pulse_radius, có cooldown.
- Thắng: tất cả 5 đèn thắp. Thua: hết máu hoặc hết thời gian (300s).
- Điểm số: per_mote=10, per_lantern=100, per_second_left=1, per_flame_left=50.

## Tuning (đóng khớp game.contract.json)
Tất cả con số đã được điền vào `game.contract.json` và `src/game_headless.py`.

## Chỗ mơ hồ đã tự giả định
- Mỗi đèn cần đúng 1 đom đóm để thắp (lantern_cost = 1).
- Người chơi chỉ tương tác với 1 đèn mỗi tick (break sau khi nạp).
- Bóng Mực không vào safe_radius quanh đèn đã thắp.
- fall_enabled = false (đảo phẳng, không rơi xuống).
- Pulse không tốn flames (pulse_cost = 0) ở Phase 1.

## Hạn nộp
- Tag `phase-1`: trước mốc 1h (khi Phase 2 phát hành).