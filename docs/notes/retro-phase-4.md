# Retrospective — Đảo Đèn Lồng (4 phase, AI SDLC)

> Tổng hợp Evaluation của 4 phase + những gì hiệu quả/không hiệu quả khi làm
> với AI, những lần AI sai và cách phát hiện, harness nào giúp nhiều nhất,
> ước tính token/chi phí và cách tiết kiệm, và nếu làm lại thì đổi gì.
> (TICKET-04 §7.)

## 1. Tổng kết theo phase

| Phase | Ticket | Contract | Việc chính | Kết quả |
|-------|--------|----------|------------|---------|
| 1 | PRD-0 | v1.0 | Engine headless + JSONL + 12 test | ✅ deterministic, 12 pass |
| 2 | TICKET-02 | v1.1 | 3 đêm, dash/charm/drifter | ✅ 26 test |
| 3 | TICKET-03 | v1.2 | Nhiên liệu đèn, drain, thắng bình minh | ✅ 40 test, ADR |
| 4 | TICKET-04 | v1.3 | Benchmark/soak/leaderboard/accessibility/GUI/release | ✅ 50 test + bench.json/soak.json |

Mỗi phase đi đúng chu trình: đọc ticket → ghi giả định → lập kế hoạch kiểm
chứng → (AI) code → kiểm chứng thật (test + headless + bằng chứng) → tag →
commit/push. **Không phase nào "AI bảo chạy rồi" là đủ** — đều có kết quả đo được.

## 2. Những gì HIỆU QUẢ khi làm với AI
- **Ticket → test → code.** AI viết test trước rồi mới code engine, nên mỗi
  yêu cầu có "ngọn" kiểm chứng. Phase 3 (nhiên liệu) có 10 test ngay từ đầu
  phủ 7 điều khoản, giúp bắt bug sớm.
- **Headless-first.** Tách logic khỏi hiển thị → test không cần GUI, chạy
  nhanh (~4 s cho 50 test), deterministic (cùng seed = cùng JSONL).
- **Chấm điểm/luật bằng số, không bằng cảm.** "Đạt" là con số (50 test,
  avg_fps ≥ 60, mem_end ≤ 1.2×mem_start), không phải "tưởng rằng".
- **Bằng chứng commit được** (`docs/proof/*`, `bench.json`, `soak.json`) —
  ai đọc sau đều tái lập được.

## 3. Những gì KHÔNG hiệu quả
- **Đổi luật giữa các version hợp đồng.** Phase 3 thay 5 luật của Phase 1/2
  (thắng bình minh, châm dầu, drain, bảng điểm mới). Mỗi lần thế phải cập nhật
  cả engine + test + contract + tài liệu; test cũ "thắng khi thắp đủ đèn" bị
  vô nghĩa → phải chuyển mục đích. **Rút kinh nghiệm: giữ contract ổn định,
  tách "thêm" khỏi "thay".**
- **GUI dựng cuối cùng.** Dựng GUI ở Phase 4 khiến 4 điều khoản trình bày của
  Phase 3 (thanh nhiên liệu, nhấp nháy 1 Hz, đổi màu, ký hiệu "⚠") không có
  nơi hiển thị ở Phase 3. Nên ghi rõ trong ADR thay vì bỏ trống.
- **pygame API thay đổi theo build.** `pygame-ce` trên Python 3.14 thiếu
  `pygame.key.keynames`, `pygame.key.keymap` (khác pygame "cổ"). Lãng phí vài
  lần sửa khi viết map phím; nên kiểm tra API của build thực trước.

## 4. Những lần AI sai + cách phát hiện
| Lần sai | Cách phát hiện |
|---|---|
| `ValueError: invalid rectstyle` khi blit glow | Chạy `bench.py` thật, đọc traceback. |
| `AttributeError: module 'pygame.version' has no attribute 'get'` | Chạy `bench.py` thật (không phải test). |
| `pygame.key.keynames`/`keymap` không có trong build | Chạy smoke test GUI (SDL dummy), đọc lỗi. |
| So sánh keycode với `ev.scancode` (sai loại) | Rà code + test `read_frame` trong dummy driver. |
| `_save`/`save_settings` giả định `Path` khi nhận `str` | Chạy `tests/test_phase_4.py` (5 test đỏ). |
| `test_tie_earlier_wins` dùng tên "A","B" (chỉ 1 ký tự) | Chạy test → `LeaderboardError`; sửa tên. |

Nguyên tắc: **AI có thể tự tin mà sai**; chỉ tin khi có kết quả thật
(test đỏ/xanh, chạy lệnh, đọc traceback). Không bao giờ "đánh dấu xong" khi
chưa chạy.

## 5. Harness nào giúp nhiều nhất
- **`AGENTS.md`** — giữ nguyên trong repo, chứng minh dùng harness AI;
  quy tắc "luôn tách logic khỏi hiển thị", "test đỏ phải sửa/ghi lý do".
- **Test + bằng chứng (`docs/proof`)** — là "nút bấm kiểm chứng" thật sự;
  là thứ giữ các phase không drift.
- **`git tag phase-N`** + commit message theo format → lịch sử rõ ràng.
- **ADR + ADR ngắn** (`adr-phase-3-lantern-fuel.md`) giúp ghi lại "tại sao",
  tránh phải suy đoán lại.
- Ít hiệu quả hơn: skill phức tạp; ở lab này **kỷ luật test + headless** quan trọng nhất.

## 6. Token / chi phí AI (ước tính)
- Ước tính **~2–3 triệu token** (input+output) cho cả 4 phase, chủ yếu do
  đọc/ghi file lớn + chạy test nhiều lần.
- Cách tiết kiệm: (1) viết test trước để giảm vòng sửa; (2) headless chạy
  nhanh (~4 s) thay vì chờ GUI; (3) không tái-sinh engine — mở rộng incrementally
  (Phase 2/3/4 đều sửa file `game_headless.py` chứ không viết lại);
  (4) dùng `grep`/`read` vùng cụ thể thay vì đọc cả file.

## 7. Nếu làm lại, đổi gì
1. **Khung GUI sớm** (một khung tối giản từ Phase 1) để các yêu cầu trình
   bày không bị "mất phương hướng" giữa các phase.
2. **Bắt đầu contract 1 lần** (versioning rõ "additive" vs "breaking") để
   giảm việc cập nhật test cũ khi đổi luật.
3. **Kiểm tra version thư viện ngay Phase 1** (pygame-ce + Python 3.14),
   tránh bất ngờ API ở Phase 4.
4. **Bắt buộc "checklist DoD" ở đầu mỗi ticket** (bằng chứng, tag, số test,
   file phải commit) để không sót (Phase 4 dễ sót `bench.json`/`soak.json`
   phải commit).

## 8. Điểm còn hạn chế (thành thật)
- GUI là sprite 2D chiếu phối cảnh, **không phải 3D vật thể** (mô hình).
  Đủ "chơi được" + đủ benchmark, không làm lại engine 3D.
- `peak_mem_mb` của soak/bench đo bằng `psutil` (máy tác giả); số máy chấm
  của giảng viên sẽ khác — công bố trước khi chấm.
- `data/leaderboard.json` (trạng thái runtime) không nên commit; chỉ commit
  cấu trúc + mẫu export.
