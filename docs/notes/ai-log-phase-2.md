# Nhật ký dùng AI — Phase 2

| Thời gian | Công cụ AI | Mục đích | Ước tính token | Ghi chú |
|-----------|------------|----------|----------------|---------|
| Phase 2 | Claude (agent) | Mở rộng engine sang v1.1 (3 đêm, dash, charm, drifters), viết test + docs | ~70k input / ~25k output (ước) | 1 phiên, main thread |

## Lỗi AI đã phát hiện & sửa (quan trọng nhất)
1. **Test Phase 1 hardcode đường dẫn cũ** (`CWD = D:/Python/.../dao-den-long-starter`) → 10 test
   fail `NotADirectoryError`. Sửa: tính CWD tương đối từ vị trí file (mẫu test Phase 2).
2. **`motes_initial: 20` khai báo trong tuning nhưng không spawn** — engine v1.1 bắt đầu với
   0 đom đóm trên đảo. Sửa: sinh 20 mote theo seed trong `__init__`.
3. **Snapshot phát gấp đôi**: `step()` tự append snapshot mỗi 10 tick, trùng với
   `--snapshot-every` trong `main()` (chạy `--snapshot-every 60` vẫn ra snapshot mỗi 10 tick).
   Sửa: bỏ hẳn snapshot trong `step()`, do `main()` quản lý duy nhất.
4. **Drifter `flee` di chuyển x2 tốc độ**: 4 dòng `+=` lặp lại. Sửa: chỉ còn 2 dòng.

## Test cũ bị contract v1.1 làm sai (đúng quy tắc AGENTS.md: sửa kèm lý do, không tắt âm)
- `test_deposit_and_light_lantern` (Phase 1): `carried: 1` → `carried: 10` (lantern_cost 1→10).
- `test_all_lanterns_lit_wins` (Phase 1): `carried: 5` → `carried: 50` (5 đèn × 10).
- `test_snapshot_has_required_fields` (Phase 1): `motes_active` → `motes/drifters/charms`.

## Cách tiết kiệm token
- Không tái viết engine cũ: chỉ chít delta (init motes, snapshot, flee).
- Dùng test làm bằng chứng (determinism bằng hash, snapshot interval bằng assert) thay vì
  đọc tay JSONL dài.
- Chạy toàn bộ suite một lần, đọc failure thật trước khi sửa (tránh đoán).

## Retro ngắn
- Lặp sai điển hình của AI: viết code "đúng theo spec chữ đen" (tuning khai báo mà không spawn).
  Phát hiện nhờ đọc kỹ `__init__` + so tuning với hành vi, không nhờ test (test Phase 2 cũ chỉ
  assert `>= 0` nên không bắt được). Bài học: test phải assert giá trị cụ thể, không phải "không crash".
- Nếu làm lại: viết test snapshot-interval và test pickup-mote cụ thể **trước** khi code Phase 2.
