# Test Contract — Phase 1 (v1.0)

Nội dung chính thức từ PRD-0 / lab board đã được áp dụng vào code.

## File hợp đồng
- `game.contract.json` tại gốc repo.

## Lệnh headless
```
python src/game_headless.py --seed <int> --night 1 --ticks <int> --out <file.jsonl>
   [--scenario <file.json>] [--inputs <file.json>] [--snapshot-every <int>]
```

## Định dạng scenario (file .json)
```json
{
  "player": {"pos": [0,0,0], "carried": 0, "flames": 3},
  "lanterns": [{"id":"L1","pos":[0,0,25],"deposited":0,"lit":false}],
  "motes": [[5,0,5], [10,0,10]],
  "shades": [{"id":"S1","pos":[10,0,0]}],
  "time_left_s": 300
}
```

## Định dạng inputs (file .json)
```json
{
  "frames": [
    {"tick":0,"move":[0,1],"cam_yaw_deg":0},
    {"tick":60,"interact":true},
    {"tick":61,"interact":false}
  ]
}
```

## Đầu ra JSONL
Mỗi dòng là một đối tượng JSON: snapshot, event, end. Xem chi tiết trong `src/game_headless.py` và `docs/proof/phase-1-headless-sample.jsonl`.

## Tính tất định
Cùng `--seed`, cùng scenario, cùng inputs → output identik giữa hai lần chạy. Đã kiểm chứng bằng test `test_deterministic_output`.

## Exit code
- 0: thành công
- 1: lỗi chạy
- 2: scenario/inputs sai định dạng