# CHANGELOG

Đảo Đèn Lồng — AI SDLC Lab (K5-L3A, MSSV 2A202603377 Chu Mai Hong).

Mỗi phase là một bản thay đổi có tag riêng (`phase-N`); các breaking changes
được đánh dấu ⚠. "Tổng điểm game, chơi lại" không đổi giữa Ticket-02/03
theo yêu cầu; đầu ra headless của v1.0–v1.2 giữ nguyên sau Phase 3 (ticket
TICKET-03 ghi "đầu ra headless không đổi" với phần luật cũ còn hiệu lực).

## Phase 4 — TICKET-04 "Bình minh: phát hành v1.0.0" (Contract v1.3)

Mới (non-breaking với các contract cũ, chỉ thêm chế độ mới):

- **Benchmark**: `python src/bench.py --seed 42 --duration 30 --out bench.json` —
  cảnh chuẩn (200 Bóng Mực wander + 100 đom đóm + L1–L3 sáng), camera orbit
  15 s/vòng, 3 s warm-up, vsync off, 1280×720. Output theo schema v1.3
  (`avg_fps`, `p1_low_fps`, `frame_ms_p95`, `load_ms`, `peak_mem_mb`, ...).
- **Soak test**: `python src/soak_test.py --seed 7 --nights 10 --out soak.json` —
  10 Đêm liên tiếp trong cùng tiến trình, đo bộ nhớ đầu/cuối;
  đạt nếu `crashes == 0` và `mem_end ≤ 1.2 × mem_start`.
- **Bảng xếp hạng cục bộ** (top 10): lưu `data/leaderboard.json`;
  nhập tên 3–12 `[A-Za-z0-9_]` sau khi thắng Đêm 3 hoặc thua;
  xuất bằng `python src/game_gui.py --export-leaderboard out.json`
  → `{"entries": [...]}` (sắp score giảm, bằng điểm thì ai đạt trước đứng trên).
- **GUI chơi được** (`src/game_gui.py` + `src/scene_render.py`): thứ nhất có
  hình ảnh, menu, HUD, camera 3D góc nhìn thứ ba; dùng chung engine
  `game_headless.py` (không sửa luật).
- **Dễ tiếp cận** (TICKET-04 §4): đổi phím mọi hành động + phát hiện trùng
  phím + khôi phục mặc định; phụ đề/chỉ báo (Bóng Mực, 10 s cuối, đèn yếu);
  giảm chuyển động (tắt rung/chớp); cỡ chữ UI ≥18 px ở 1280×720, chữ lớn ×1.25.
- `requirements.txt` (pygame-ce, psutil).
- `game.contract.json` thêm `bench_cmd`, `soak_cmd`, `export_leaderboard_cmd`.

⚠ Breaking (đây là thay đổi contract cũ):

- Không có. v1.3 giữ nguyên mọi yêu cầu của v1.0–v1.2; chỉ thêm chế độ đo.

## Phase 3 — TICKET-03 "Đèn cạn dầu" (Contract v1.2)

Mới:

- Nhiên liệu đèn: `fuel_max=100`, hao 1.0/s (1/60 mỗi tick), thắp/thắp lại
  đặt fuel=100, châm dầu `used = min(đang mang, ceil((100−fuel)/10))`,
  đèn full không được chọn, đèn hết dầu (fuel≤0) tắt + `deposited=0`
  + sự kiện `lantern_out` + nhớ `ever_lit`.
- Thắp lại (đã từng sáng) chỉ tốn 5 đom; lần đầu tốn 10.
- Sức chứa tăng dần: `min(20, 10 + 2 × successful_lights)`.
- Bóng Mực hút dầu: đèn fuel < 30 mất vùng an toàn; shade `wander` chọn đèn
  yếu nhất; state mới `drain` (đứng yên, hút 5 fuel/s/từng con, cộng dồn);
  thoát drain khi đèn tắt / fuel ≥30 / xa đèn >2 m / Mây vào trong 6 m;
  pulse khi đang drain được +15; châm dầu lên ≥30 đẩy shade ra mép vùng
  an toàn tối đa 30 tick, không gây sát thương trong lúc đó.
- Thắng mới (bình minh): không thắng sớm; giữ `≥ ceil(0.6 × tổng đèn)`
  sáng tới hết giờ (`dawn_survived`); thua `no_flames` (ưu tiên, kể cả tick
  cuối) hoặc `dawn`. Thời gian đêm đổi: 240 / 270 / 300 s.
- Điểm mới: nạp +5/mỗi đom; lần đầu +100; thắp lại +40; bình minh (chỉ khi
  thắng) +50 + floor(fuel) mỗi đèn sáng, +50 mỗi ngọn lửa còn lại; bỏ thưởng thời gian.

⚠ Breaking (đây là thay đổi contract cũ):

- `night1/2/3_duration_s`: 300/330/360 → 240/270/300 s.
- Luật "thắng ngay khi tất cả đèn sáng" bị **thay thế** → thắng theo ngưỡng
  bình minh; `game_over.reason` bỏ `all_lit`, thêm `dawn_survived`.
- "Đèn đã sáng không nhận thêm đom đóm" bị **thay thế** → châm dầu.
- "Bóng Mực không bao giờ vào vùng an toàn" bị **thay thế** →
  đèn yếu (fuel<30) cho phép Bóng Mực hút dầu (drain).
- Công thức điểm cũ (v1.0/v1.1: `per_second_left_win`, ...) bị **thay thế**
  hoàn toàn bằng bảng điểm Phase 3.
- Snapshot: đèn thêm `fuel` (số thực 1 chữ số thập phân; đèn tắt fuel=0),
  `ever_lit`, `relit_count`; player thêm `capacity`; Bóng Mực thêm state `drain`.
- Scenario: đèn đặt `lit/fuel/ever_lit`, `player.successful_lights`,
  `shades[].target_lantern_id`; đèn `lit:true` không có fuel mặc định 100.
- Sự kiện mới: `refuel {lantern_id, amount, fuel}`, `lantern_out {lantern_id}`,
  `fuel_drain {lantern_id, shade_id, fuel}` (mỗi 60 tick khi đang hút);
  `lantern_lit` thêm `relight: true|false`.

## Phase 2 — TICKET-02 "Ba hòn đảo" (Contract v1.1)

Mới:

- Mở rộng 3 đêm (5/6/7 đèn); dash, pulse chi phí, Bùa Gió (charms),
  Gió Lạc (drifters), pause, nhảy + trọng lực; đom đóm ban đầu 20.
- Snapshot v1.1: thêm `motes`, `drifters`, `charms`, `wind`, các trường
  player mới (`vel`, `grounded`, `invuln`, `dash_cd_s`, `pulse_cd_s`, `charm_s`).

⚠ Breaking:

- `lantern_cost`: 1 (v1.0) → 10 (v1.1).
- Bỏ field snapshot `motes_active` (v1.0) → thay bằng `motes` (v1.1).
- `pulse` tốn 3 đom (v1.0: 0) + cooldown 3 s.

## Phase 1 — PRD-0 (Contract v1.0)

Mới:

- Engine headless `src/game_headless.py` (JSONL, deterministic),
  `game.contract.json` v1.0 (tuning đầy đủ), `tests/test_phase_1.py`,
  `src/hello_headless.py` (CP0).
- 1 màn Đêm 1: 5 Đèn Lồng Lớn, nhặt đom, nạp đèn, né Bóng Mực, toả sáng,
  thắng khi thắp đủ đèn.

## Chưa hoàn thành / ghi trung thực

- Video demo `.mp4` (<5 phút) sẽ sinh bằng ffmpeg + `docs/demo/`.
- Release v1.0.0 (bản chạy được) sẽ tạo sau khi gắn tag `phase-4`.
- GUI dùng sprite 2D (không phải mô hình 3D vật thể); đủ để "chơi được"
  và đo hiệu năng, không làm lại engine.
