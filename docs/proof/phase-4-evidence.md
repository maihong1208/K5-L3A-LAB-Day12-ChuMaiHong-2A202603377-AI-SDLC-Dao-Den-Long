# Bằng chứng Phase 4 (TICKET-04 — "Bình minh: phát hành v1.0.0", Contract v1.3)

Số liệu dưới đây do tác giả tự chạy (tham khảo); ngưỡng đạt được chấm trên
máy của giảng viên (công bố trước khi đo). Mọi chế độ benchmark/soak **tắt
các nhân vật/kẻ địch/hiệu ứng sáng tạo thêm** → đo trên cùng cảnh chuẩn.

## 1. Benchmark (TICKET-04 §1)
Lệnh: `python src/bench.py --seed 42 --duration 30 --out bench.json`

Kết quả máy tác giả (đã commit `bench.json`):
```
avg_fps      = 376.4   (ngưỡng >= 60)      ✅
p1_low_fps   = 202.8   (ngưỡng >= 30)      ✅
load_ms      = 679     (ngưỡng <= 10000)   ✅
frames       = 11290, peak_mem_mb = 45, vsync_off = true
```
- 3 s warm-up (không đo), sau đó đo đúng `--duration` s, tự thoát mã 0.
- p1_low_fps: `k = max(1, ceil(0.01×N))`, lấy k khung dt lớn nhất,
  `p1_low_fps = 1000 / trung_bình(k dt lớn nhất)`.
- `frame_ms_p95`: phân vị 95 của dt (ms).

## 2. Soak test (TICKET-04 §2)
Lệnh: `python src/soak_test.py --seed 7 --nights 10 --out soak.json`

Kết quả máy tác giả (đã commit `soak.json`):
```
crashes      = 0        (ngưỡng == 0)        ✅
mem_start_mb = 22
mem_end_mb   = 26       (ngưỡng <= 1.2×22 = 26.4)  ✅ (vừa đạt)
```
- 10 Đêm liên tiếp trong 1 tiến trình (1→2→3 xoay vòng), seed `7+i`.
- Input ngẫu nhiên theo seed (30 tick/hướng; 5% nhảy, 3% lướt, 2% toả sáng, 10% tương tác).
- `mem_end_mb` đo RSS sau khi reset xong Đêm cuối cùng.

## 3. Bảng xếp hạng (TICKET-04 §3)
- `src/leaderboard.py`: top 10, tên 3–12 `[A-Za-z0-9_]`, mỗi mục
  `name/score/nights_won/achieved_at/seed`, sắp score giảm (bằng điểm → ai đạt trước).
- Lưu `data/leaderboard.json` (đĩa cục bộ, còn sau khi tắt/mở).
- Xuất: `python src/game_gui.py --export-leaderboard out.json` → `{"entries":[...]}`.
- Test: `tests/test_phase_4.py` (tên hợp lệ/không hợp lệ, top 10, thứ tự).

## 4. Dễ tiếp cận (TICKET-04 §4)
- Đổi phím mọi hành động (WASD/jump/dash/interact/pulse/pause) + phát hiện
  trùng phím + khôi phục mặc định: `src/settings_store.py`
  (`ACTIONS`, `key_conflicts`, `reset_keybinds`). Test: `test_key_conflicts*`.
- Phụ đề/chỉ báo: Bóng Mực (viền + mắt + nhấp nháy drain), gió, "10 giây cuối",
  đèn fuel<30 → `src/game_gui.py::_draw_hud`.
- Giảm chuyển động: `reduce_motion` (tắt rung camera/chớp màn hình).
- Cỡ chữ UI ≥18 px @1280×720, chữ lớn ×1.25: `settings_store.ui_font_size`
  (test `test_ui_font_size`).

## 5. Đóng gói & tài liệu (TICKET-04 §5)
- `requirements.txt` (pygame-ce, psutil). 3 lệnh: clone → `pip install -r requirements.txt` → `python src/game_gui.py`.
- `README.md` (cài đặt, điều khiển, test, headless, bench, soak), `CHANGELOG.md` (4 phase),
  `CREDITS.md`, `LICENSE` (MIT), `RUBRIC.md`.
- Video demo: `docs/demo/demo.mp4` (sinh bằng `docs/demo/make_demo.py` + ffmpeg; < 5 phút).

## 6. Test Contract v1.3
- `game.contract.json`: `contract_version` = "1.3", thêm `bench_cmd`, `soak_cmd`.
- Mọi yêu cầu v1.0–v1.2 **giữ nguyên** (không đổi luật/số liệu/headless cũ).

## Test tổng
`python -m pytest tests/` → **50/50 pass** (40 Phase 1–3 + 10 Phase 4 trong `tests/test_phase_4.py`).

## Ghi chú trung thực
- GUI dùng sprite 2D chiếu phối cảnh (không phải mô hình 3D vật thể); đủ "chơi
  được" và đủ để benchmark đo hiệu năng.
- `peak_mem_mb` đo bằng `psutil` (RSS tiến trình); trên bản web (không dùng ở
  lab) sẽ ghi `null`.
