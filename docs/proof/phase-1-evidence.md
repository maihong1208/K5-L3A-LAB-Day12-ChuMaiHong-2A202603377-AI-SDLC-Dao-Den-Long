# Bằng chứng kiểm chứng Phase 1

## Môi trường chạy
- Máy: Windows (PowerShell)
- Hệ điều hành: Windows 11
- Python: 3.14.7
- Repo: `dao-den-long-starter` (sẽ copy sang repo cá nhân)

## Kết quả test (12/12 pass)
```
python -m pytest tests/ -v
# 12 passed
```

| Test | Kết quả |
|------|---------|
| test_headless_runs_ok | ✅ Pass |
| test_deterministic_output | ✅ Pass |
| test_snapshot_has_required_fields | ✅ Pass |
| test_end_line_is_last | ✅ Pass |
| test_coordinates_rounded_3_decimals | ✅ Pass |
| test_movement_changes_position | ✅ Pass |
| test_pickup_mote | ✅ Pass |
| test_deposit_and_light_lantern | ✅ Pass |
| test_all_lanterns_lit_wins | ✅ Pass |
| test_lantern_count_night1_is_5 | ✅ Pass |
| test_hello_headless::test_headless_runs_and_returns_ok | ✅ Pass (CP0) |
| test_hello_headless::test_deterministic_output | ✅ Pass (CP0) |

## Bằng chứng headless (mẫu)
File: `docs/proof/phase-1-headless-sample.jsonl`
- Lệnh: `python src/game_headless.py --seed 123 --night 1 --ticks 600 --out docs/proof/phase-1-headless-sample.jsonl --snapshot-every 60`
- Output: JSONL có snapshot (mỗi 60 tick), event, end.
- Tất cả toạ độ làm tròn 3 chữ số thập phân.
- Deterministic: chạy lại với cùng seed → output identik.

## Chỗ chưa đạt (nếu có)
- Không có. Tất cả yêu cầu cốt lõi Phase 1 đã code và test.

## Chạy lại tại tag `phase-1`
```
git checkout phase-1
python -m pytest tests/
python src/game_headless.py --seed 123 --night 1 --ticks 600 --out out.jsonl
```