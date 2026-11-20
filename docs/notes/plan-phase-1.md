# Kế hoạch Phase 1 (PRD-0) — ĐÃ THỰC HIỆN

## Tiêu chí nghiệm thu
| Yêu cầu | Cách kiểm chứng | Kết quả |
|---------|-----------------|---------|
| Game chạy headless | `python src/game_headless.py --seed 1 --night 1 --ticks 100 --out /tmp/x.jsonl` | ✅ Pass |
| Đầu ra JSONL theo contract | Kiểm tra type snapshot/event/end | ✅ Pass |
| Tính tất định | Chạy hai lần cùng seed/scenario/inputs, so sánh output | ✅ Pass (`test_deterministic_output`) |
| 5 Đèn Lồng Lớn (L1-L5) | Kiểm tra snapshot có 5 lanterns | ✅ Pass |
| Nhặt đom đóm | Tương tác trong pickup_radius → event `mote_picked` | ✅ Pass |
| Nạp ánh sáng, thắp đèn | Tương tác trong interact_radius → event `deposit`, `lantern_lit` | ✅ Pass |
| Thắng khi tất cả đèn thắp | Tất cả 5 đèn lit → state "won" | ✅ Pass (`test_all_lanterns_lit_wins`) |
| Bóng Mực đuổi và tát máu | Shade chase player, event `player_hit` | Code đã viết, test skeleton |
| Tỏa sáng xua Bóng Mực | Pulse trong pulse_radius → event `pulse`, state stunned | Code đã viết |

## Bước thực hiện
1. ✅ Đọc PRD-0, ghi assumptions.
2. ✅ Viết test contract headless.
3. ✅ Code `src/game_headless.py` theo Test Contract v1.0.
4. ✅ Viết `tests/test_phase_1.py` (10 test, tất cả pass).
5. ✅ Chạy test, lưu bằng chứng vào `docs/proof/`.
6. ⬜ Gắn tag `phase-1` và push trước mốc 1h.

## Nhật ký thay đổi
- Tạo `game.contract.json` với tuning đầy đủ.
- Tạo `src/game_headless.py` engine headless deterministic.
- Tạo `tests/test_phase_1.py` với 10 test cases.