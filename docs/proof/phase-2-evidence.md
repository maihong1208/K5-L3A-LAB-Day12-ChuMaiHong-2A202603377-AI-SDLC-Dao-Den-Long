# Bằng chứng kiểm chứng Phase 2 (Ticket-02 / Test Contract v1.1)

## Môi trường
- Windows 11, Python 3.14.7, chạy headless (không GUI).

## Kết quả test
```
python -m pytest tests/ -q
# 26 passed (CP0 + Phase 1 (đã cập nhật theo v1.1) + Phase 2)
```
Chạy lại tại tag `phase-2` với lệnh trên; chi tiết tên từng test: `python -m pytest tests/ -v`.

## Bằng chứng deterministic
- Lệnh: `python src/game_headless.py --seed 42 --night 2 --ticks 600 --out docs/proof/phase-2-headless-sample.jsonl --snapshot-every 60`
- Chạy 3 lần cùng tham số → output byte-identik (so SHA-256).
- SHA-256 mẫu tại tag `phase-2`: `b06b6041f3d7168a9a197dfb1930dbcf0dd43d214eae0f8aa57205572deb9836`
- Kiểm tra nhanh:
  ```
  python src/game_headless.py --seed 42 --night 2 --ticks 600 --out a.jsonl --snapshot-every 60
  python src/game_headless.py --seed 42 --night 2 --ticks 600 --out b.jsonl --snapshot-every 60
  # a.jsonl và b.jsonl giống hệt
  ```

## Bằng chứng snapshot interval
- Test `test_snapshot_interval_follows_flag`: `--ticks 60 --snapshot-every 30` → snapshots đúng tại tick 0, 30, 60 (không cứng mã hóa trong `step()`).

## Chỗ chưa đạt / ghi trung thực
- `src/game_gui.py` (run_cmd trong contract) chưa có — GUI thuộc Phase 4; Phase 2 chỉ đảm bảo engine headless đúng contract v1.1.
- Wind trong snapshot khai báo nhưng chưa có động lực (giả định, xem `docs/notes/assumptions-phase-2.md`).
- Chìm dưới -10 m chưa xử lý (đảo phẳng Phase 2).
