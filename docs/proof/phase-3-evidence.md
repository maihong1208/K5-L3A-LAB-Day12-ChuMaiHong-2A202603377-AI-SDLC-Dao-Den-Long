# Bằng chứng Phase 3 (TICKET-03 — "Đèn cạn dầu", Contract v1.2)

## Kết quả test
- Lệnh: `python -m pytest tests/` → **40/40 pass** (gồm 10 test Phase 3 trong `tests/test_phase_3.py`).
- `src/game_headless.py` compile sạch: `python -m py_compile src/game_headless.py`.

## Kiểm chứng từng điều khoản (ticket §1–§7)
| Điều khoản | Kiểm chứng |
|---|---|
| §1 Đèn có nhiên liệu (fuel 0–100, hao 1.0/s) | `tests/test_phase_3.py::test_fuel_decay_uses_integer_sixtieths`, `test_lit_scenario_defaults_to_full_fuel_and_remembers_light` |
| §1 Thắp/thắp lại đặt fuel=100; lần đầu tốn 10, đã từng sáng tốn 5 | `test_first_light_then_relight_costs_and_capacity`, `test_relight_cost_and_score` |
| §1 Nạp đèn = min(đang mang, ceil((100−fuel)/10)); đèn full không nạp | `test_refuel_rounds_mote_use_up_and_awards_points` (fuel 81→100, dùng đúng 2) |
| §1 Hết dầu tắt đèn, `deposited=0`, nhớ đã từng sáng | `test_empty_lantern_goes_out_and_resets_deposit` |
| §2 Sức chứa tăng dần min(20, 10+2×successful_lights) | `test_first_light_then_relight_costs_and_capacity` |
| §3 Thắng bằng bình minh (≥60% đèn sáng), không thắng sớm | `TestPhase3Dawn::test_all_lit_does_not_end_before_dawn`, `test_dawn_threshold_wins_and_scores_remaining_fuel`, `test_dawn_below_threshold_loses` |
| §4 Thắng bình minh cộng điểm (50+floor(fuel)/đèn, 50/lửa), thua `no_flames`/`dawn` | `TestPhase3Dawn` + `test_no_flames_takes_precedence_at_dawn` |
| §5 Đèn yếu (fuel<30) không còn vùng an toàn; Bóng Mực hút dầu, thoát đúng 4 điều kiện | `TestPhase3Drain::test_wander_shade_enters_drain_near_weak_lantern`, `test_drain_removes_five_fuel_per_second_plus_decay` |
| §5 Châm dầu ≥30 đẩy Bóng Mực ra vùng an toàn, không gây sát thương | `test_refueling_to_threshold_pushes_shade_out_and_protects_player` |
| §5 Toả sáng Bóng Mực đang drain → +15 | `test_drain_pulse_awards_fifteen_and_stuns` |
| §7 Điểm mới, thời gian đêm 240/270/300 s | contract `game.contract.json` v1.2 + `TestPhase3Dawn` |

## Breaking changes đã thực hiện (so v1.1)
1. `night1/2/3_duration_s`: 300/330/360 → **240/270/300** (`game.contract.json`).
2. Bỏ luật "thắng ngay khi tất cả đèn sáng" → thắng theo **ngưỡng bình minh** (ceil 0.6×tổng). `game_over.reason` bỏ `all_lit`, thêm `dawn_survived`. Hai test cũ `test_all_lanterns_lit_wins` (Phase 1/2) được **chuyển mục đích** kiểm tra luật mới (không skip, không tắt âm).
3. "Đèn đã sáng không nhận thêm đom đóm" → **châm dầu** (`refuel`).
4. "Bóng Mực không bao giờ vào vùng an toàn" → đèn yếu (fuel<30) cho phép **drain**.
5. Bảng điểm v1.0/v1.1 bị **thay thế** bằng bảng điểm Phase 3.
6. Snapshot v1.2: đèn thêm `fuel`, `ever_lit`, `relit_count`; player thêm `capacity`; Bóng Mực thêm state `drain` + `target_lantern_id`. Sự kiện mới: `refuel`, `lantern_out`, `fuel_drain` (mỗi 60 tick khi đang hút).

## Bằng chứng deterministic
- `docs/proof/phase-3-headless-sample.jsonl`: chạy `--seed 42 --night 1` với
  scenario châm dầu + Bóng Mực drain (sự kiện `refuel`, `player_hit`, `game_over`).
  Cùng seed + scenario + input → cùng file. Số lượng sự kiện ổn định qua 2 lần chạy.

## Ghi chú trung thực
- GUI chưa có ở Phase 3 (dự kiến Phase 4); các yêu cầu trình bày (thanh nhiên
  liệu, nhấp nháy 1 Hz, viền/mắt đổi màu, ký hiệu "⚠") được ghi nhận trong
  `docs/notes/adr-phase-3-lantern-fuel.md` và triển khai ở Phase 4.
- Chế độ mù màu (Ticket-03 §6) lưu trong `config/settings.json` (`colorblind_mode`),
  không ảnh hưởng đầu ra headless.
