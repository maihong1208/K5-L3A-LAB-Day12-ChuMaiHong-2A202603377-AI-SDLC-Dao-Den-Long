# AGENTS.md — Hướng dẫn cho AI Agent (Harness)

## Mục đích
File này được giữ nguyên trong repo và lịch sử git để chứng minh bạn đã dùng harness AI trong lab AI SDLC. Agent đọc file này trước khi làm việc trên repo.

## Dự án
Game 3D "Đảo Đèn Lồng" — giai đoạn chuẩn bị (CP0) và 4 phase phát triển.

## Môi trường
- Ngôn ngữ: Python 3
- Chạy headless: `python src/hello_headless.py`
- Chạy test: `python -m pytest tests/` hoặc `python -m unittest discover tests`

## Quy tắc khi agent viết code
1. Luôn tách logic game khỏi phần hiển thị để chạy được headless.
2. Không sửa tay output test để làm nổi bật kết quả.
3. Không commit API key, token, `.env`.
4. Test phải chạy được bằng 1 lệnh trên máy sạch (clone repo mới).
5. Khi test đỏ, agent không được bỏ qua hoặc tắt âm — phải sửa hoặc ghi lý do.

## Các lệnh thường dùng
- `python src/hello_headless.py` — kiểm tra môi trường headless (CP0)
- `python -m pytest tests/` — chạy toàn bộ test đơn vị
- `git tag phase-N && git push origin phase-N` — gắn tag mỗi phase

## Ghi nhớ
- Mỗi phase: đọc yêu cầu → ghi giả định → lập kế hoạch kiểm chứng → agent code → kiểm chứng thật → gắn tag → push.
- "Agent bảo chạy rồi" không phải bằng chứng.

## Phase 1 (PRD-0) — ĐÃ HOÀN THÀNH
- File hợp đồng: `game.contract.json` (tuning đầy đủ)
- Engine headless: `src/game_headless.py` (Test Contract v1.0, JSONL, deterministic)
- Test: `tests/test_phase_1.py` (10 test, 100% pass)
- Bằng chứng: `docs/proof/phase-1-evidence.md`, `docs/proof/phase-1-headless-sample.jsonl`
- Giả định: `docs/notes/assumptions-phase-1.md`
- Kế hoạch: `docs/notes/plan-phase-1.md`
- Nhật ký AI: `docs/notes/ai-log-phase-1.md`

Cách chạy headless Phase 1:
  python src/game_headless.py --seed <int> --night 1 --ticks <int> --out <file.jsonl>

## Phase 2 (TICKET-02) — ĐÃ HOÀN THÀNH
- 3 Đêm (5/6/7 đèn), dash, pulse chi phí, Bùa Gió, Gió Lạc, pause, nhảy+trọng lực.
- Test: `tests/test_phase_2.py` (gộp với Phase 1). Bằng chứng: `docs/proof/phase-2-evidence.md`.

## Phase 3 (TICKET-03) — ĐÃ HOÀN THÀNH
- File hợp đồng: `game.contract.json` (Test Contract v1.2, nhiên liệu đèn)
- Engine: `src/game_headless.py` (fuel hao/hút, châm dầu, drain, thắng bình minh)
- Test: `tests/test_phase_3.py` (10 test). Bằng chứng: `docs/proof/phase-3-evidence.md`, `docs/proof/phase-3-headless-sample.jsonl`
- ADR: `docs/notes/adr-phase-3-lantern-fuel.md`
- Setting màu: `config/settings.json` + `src/settings_store.py`

## Phase 4 (TICKET-04) — ĐÃ HOÀN THÀNH (v1.0.0)
- GUI chơi được: `src/game_gui.py` + `src/scene_render.py` (pygame-ce).
- Benchmark: `src/bench.py` → `bench.json`. Soak: `src/soak_test.py` → `soak.json`.
- Bảng xếp hạng: `src/leaderboard.py` + `--export-leaderboard`. Accessibility: `src/settings_store.py`.
- Video demo: `docs/demo/demo.mp4` (sinh bằng `docs/demo/make_demo.py`).
- Test: `tests/test_phase_4.py`. Bằng chứng: `docs/proof/phase-4-evidence.md`. Retro: `docs/notes/retro-phase-4.md`.
- Lệnh Phase 4:
    python src/game_gui.py                 # chơi
    python src/bench.py --seed 42 --duration 30 --out bench.json
    python src/soak_test.py --seed 7 --nights 10 --out soak.json
    python src/game_gui.py --export-leaderboard out.json

## CẤU TRÚC SỬA ĐỔI (quan trọng cho agent sau)
- `src/game_headless.py` = **source of truth** cho luật (headless, deterministic).
  GUI (`game_gui.py`) CHỈ đọc/cập nhật state, không sửa luật.
- Mọi thay đổi luật phải cập nhật: engine + `tests/` + `game.contract.json` + README/CHANGELOG.
- Khi thêm chế độ đo (bench/soak): nhân vật/kẻ địch/hiệu ứng SÁNG TẠO THÊM phải tắt
  hoặc không ảnh hưởng số đo (Ticket-04: mọi bài đo trên cùng cảnh chuẩn).