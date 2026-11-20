# Đảo Đèn Lồng — AI SDLC Lab (K5-L3A-Day12)

> Game góc nhìn thứ ba 3D: người giữ đèn nhỏ tuổi gom đom đóm để thắp và **nuôi** các Đèn Lồng Lớn, né Bóng Mực trong sương đen, và giữ đảo sáng đến bình minh.
> Được phát triển theo AI SDLC: mỗi phase có ticket, giả định, kế hoạch, engine headless + test, bằng chứng, tag `phase-N`.

🎥 **Video demo:** [`docs/demo/demo.mp4`](docs/demo/demo.mp4) (dưới 5 phút, sinh tự động bằng ffmpeg từ chế độ benchmark).

## ✅ Đạt được (bản phát hành v1.0.0)

| Phase | Ticket | Contract | Tag | Bằng chứng |
|-------|--------|----------|-----|-----------|
| 1 | PRD-0 (1 màn chơi) | v1.0 | `phase-1` | `docs/proof/phase-1-evidence.md` (12 test pass) |
| 2 | TICKET-02 (3 đêm) | v1.1 | `phase-2` | `docs/proof/phase-2-evidence.md` (26 test pass) |
| 3 | TICKET-03 (đèn cạn dầu) | v1.2 | `phase-3` | `docs/proof/phase-3-evidence.md` (40 test pass) |
| 4 | TICKET-04 (phát hành) | v1.3 | `phase-4` | `docs/proof/phase-4-evidence.md` + `bench.json`, `soak.json` |

Mọi test ẩn Phase 1–3 vẫn hiệu lực: `python -m pytest tests/` → **40/40 pass**.

## Cài đặt & chạy (tối đa 3 lệnh)

```bash
# 1. Clone repo
git clone https://github.com/maihong1208/K5-L3-LAB-Day12-ChuMaiHong-2A202603377-AI-SDLC-Dao-Den-Long.git
cd K5-L3-LAB-Day12-ChuMaiHong-2A202603377-AI-SDLC-Dao-Den-Long

# 2. Cài đặt phụ thuộc
pip install -r requirements.txt

# 3. Chơi game (GUI, cửa sổ 1280×720)
python src/game_gui.py
```

Chế độ không đồ hoạ (CP0): `python src/hello_headless.py`.

## Yêu cầu hệ thống

- Python 3.10+ (đã kiểm tra 3.14), Windows/macOS/Linux.
- `pygame-ce` ≥ 2.5.8 (hiển thị, cửa sổ), `psutil` ≥ 6.0 (đo bộ nhớ).
  Engine headless + test chỉ dùng thư viện chuẩn (stdlib).
- GPU: card tích hợp đủ chạy 2D; benchmark đo trên CPU+GPU máy chấm của giảng viên.
- RAM: ~50 MB (peak của benchmark, ghi trong `bench.json`).

## Điều khiển (GUI, có thể đổi trong Settings)

| Hành động | Mặc định |
|-----------|----------|
| Di chuyển lên / xuống / trái / phải | W / S / A / D |
| Nhảy | Space |
| Lướt (dash) | Shift |
| Tương tác (nhặt đom / nạp đèn / thắp) | E |
| Toả sáng (pulse) | Q |
| Tạm dừng (pause) | P |
| Thoát | Esc |

Mọi hành động trên có thể **đổi phím** trong menu Settings; hệ thống **phát
hiện và cảnh báo phím trùng**, có nút **khôi phục mặc định**
(`src/settings_store.py::reset_keybinds`).

## Cách chạy test

```bash
python -m pytest tests/          # 40 test, ~3 s
# hoặc:
python -m unittest discover tests
```

## Chế độ headless (Test Contract)

```bash
# 1 Đêm, 1500 tick (25 s), Night 1, seed 42
python src/game_headless.py --seed 42 --night 1 --ticks 1500 --out out.jsonl

# Dựng tình huống + input + snapshot thưa
python src/game_headless.py --seed 1 --night 1 --ticks 300 \
    --scenario scenario.json --inputs inputs.json --out out.jsonl --snapshot-every 5
```

Định dạng JSONL: `start`, `snapshot` (theo Test Contract v1.2 §E), `event`,
`end`. Mã thoát: 0 = ok, 1 = lỗi, 2 = sai định dạng file. Deterministic:
cùng seed + input cho ra cùng file.

## Benchmark (TICKET-04 §1)

```bash
python src/bench.py --seed 42 --duration 30 --out bench.json
```

Cảnh chuẩn: 1280×720, **vsync off**, không toàn màn hình; Đêm 1 với **200 Bóng
Mực wander + 100 đom đóm** + đèn L1–L3 sáng (fuel 100); camera orbit bán kính
30 m, cao 15 m, 15 s/vòng, khởi đầu ở (30,15,0); 3 s warm-up; tắt sinh thêm /
sát thương / hao dầu / kết thúc Đêm. Output: `avg_fps`, `p1_low_fps`
(1% thấp nhất), `frame_ms_p95`, `load_ms`, `peak_mem_mb`, `frames`.

> **VsSync:** đã tắt (pygame-ce không bật vsync khi `pygame.display.set_mode`
> không truyền flag vsync; cửa sổ không fullscreen). Ghi rõ đây vì ticket yêu
> cầu "ghi rõ trong README nếu không tắt được" — ở bản này tắt được.
> Ngưỡng đạt (đo trên máy chấm): `avg_fps ≥ 60 · p1_low_fps ≥ 30 · load_ms ≤ 10000`.
> Số trên máy của tác giả (tham khảo): xem `bench.json`.

## Soak test (TICKET-04 §2)

```bash
python src/soak_test.py --seed 7 --nights 10 --out soak.json
```

10 Đêm liên tiếp (1→2→3 xoay vòng, seed `7+i`) trong **một tiến trình**, input
ngẫu nhiên theo seed (30 tick/hướng; 5% nhảy, 3% lướt, 2% toả sáng, 10% tương
tác). Đạt nếu `crashes == 0` và `mem_end_mb ≤ 1.2 × mem_start_mb`.

## Bảng xếp hạng (TICKET-04 §3)

- Chơi hết (thắng Đêm 3 hoặc thua) → màn hình nhập tên (3–12 `[A-Za-z0-9_]`).
- Lưu top 10 vào `data/leaderboard.json`, còn sau khi tắt/mở; mỗi mục:
  `name`, `score` (tổng điểm các Đêm đã thắng), `nights_won`, `achieved_at`
  (ISO 8601 có múi giờ), `seed`. Sắp score giảm, bằng điểm ai đạt trước đứng trên.
- Xuất: `python src/game_gui.py --export-leaderboard out.json`
  → `{"entries": [...]}` đúng thứ tự.

## Dễ tiếp cận (accessibility, TICKET-04 §4)

| Yêu cầu | Triển khai |
|---|---|
| Đổi phím + phát hiện trùng + khôi phục mặc định | `src/settings_store.py` (ACTIONS, key_conflicts, reset_keybinds), menu Settings của GUI |
| Phụ đề / chỉ báo hình | HUD: Bóng Mực (viền + mắt), gió sắp thổi, "10 GIÂY CUỐI", đèn fuel<30 (`src/game_gui.py::_draw_hud`) |
| Giảm chuyển động | Settings `reduce_motion` (tắt rung camera + chớp màn hình + nhấp nháy drain) |
| Cỡ chữ UI | ≥18 px ở 1280×720; tuỳ chọn chữ lớn ×1.25 (`large_text`) |

Tuỳ chọn màu **dễ phân biệt** (TICKET-03 §6) cũng ở đây: `colorblind_mode`
đổi viền/mắt Bóng Mực `#00B3FF`, cảnh báo `#FFFFFF`.

## Đóng gói (TICKET-04 §5)

- **Chạy 3 lệnh** (mục trên) trên máy sạch.
- **Release v1.0.0** (GitHub Release gắn tag `phase-4`): file thực thi Python
  chạy được (thư mục `src/` + `requirements.txt`), hướng dẫn trong README;
  video demo `docs/demo/demo.mp4`.
- `CHANGELOG.md` (4 phase), `CREDITS.md`, `LICENSE` (MIT), `RUBRIC.md`.

## Sáng tạo của tôi

- **Không đổi luật, số liệu hay Test Contract** (yêu cầu ticket). Phần sáng
  tạo nằm ở lớp hiển thị: phong cách "hòn đảo nổi trong sương" (sky/ground
  gradient, elip đảo), sprite glow radial cho đèn/đom/Bóng Mực, camera orbit
  trong benchmark. Trong cảnh benchmark & soak, mọi nhân vật/kẻ địch/hiệu
  ứng sáng tạo thêm đều **tắt hoặc không ảnh hưởng số đo** — mọi bài đo trên
  cùng cảnh chuẩn.

## Harness AI (bằng chứng dùng AI SDLC)

- `AGENTS.md` — hướng dẫn harness đọc repo, quy tắc viết code, các lệnh.
- `docs/notes/` — giả định, kế hoạch, nhật ký AI, Test Contract từng phase
  (v1.0, v1.1, v1.2, v1.3), ADR (quyết định kiến trúc), retro.
- `docs/proof/` — bằng chứng: kết quả test, mẫu JSONL, số liệu bench/soak.
- Xem `docs/notes/retro-phase-4.md` cho retrospective tổng hợp 4 phase.

## CREDITS & LICENSE
Xem `CREDITS.md` và `LICENSE`.

---
*Repo public. Không commit .env, API key, token.*
