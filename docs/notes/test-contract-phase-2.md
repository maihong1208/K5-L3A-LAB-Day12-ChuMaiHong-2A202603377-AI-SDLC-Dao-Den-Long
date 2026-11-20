# Test Contract — Phase 2 (v1.1)

## File hợp đồng
- `game.contract.json` tại gốc repo, `contract_version: "1.1"`.

## Lệnh headless
```
python src/game_headless.py --seed <int> --night <1|2|3> --ticks <int> --out <file.jsonl>
   [--scenario <file.json>] [--inputs <file.json>] [--snapshot-every <int>]
```

## Định dạng scenario (file .json)
```json
{
  "player": {"pos": [0,0,0], "carried": 0, "flames": 3,
             "invuln_ticks": 0, "dash_cd_ticks": 0, "pulse_cd_ticks": 0, "charm_ticks": 0},
  "lanterns": [{"id": "L1", "pos": [0,0,25], "deposited": 0, "lit": false}],
  "motes": [[5,0,5], {"id":"M2","pos":[10,0,10],"kind":"dropped","ttl_s":8}],
  "shades": [{"id":"S1","pos":[10,0,0],"state":"wander","state_ticks_left":0}],
  "drifters": [{"id":"D1","pos":[5,0,5],"state":"idle","stolen":0}],
  "charms": [{"id":"C1","pos":[5,0,0],"available":true,"respawn_ticks_left":0}],
  "time_left_s": 330
}
```

## Định dạng inputs (file .json)
```json
{
  "frames": [
    {"tick": 0, "move": [1, 0], "cam_yaw_deg": 0},
    {"tick": 60, "interact": true}, {"tick": 61, "interact": false},
    {"tick": 120, "dash": true}, {"tick": 121, "dash": false},
    {"tick": 180, "pulse": true}, {"tick": 181, "pulse": false},
    {"tick": 240, "jump": true}, {"tick": 241, "jump": false},
    {"tick": 300, "pause": true}, {"tick": 360, "pause": false}
  ]
}
```

## Snapshot (mỗi N tick theo `--snapshot-every`, mặc định 10)
Bắt buộc: `type, tick, sim_tick, state, night, time_left_s, score, wind,
player{pos, vel, flames, carried, grounded, invuln, dash_cd_s, pulse_cd_s, charm_s},
lanterns, shades, motes, drifters, charms`.
Toạ độ làm tròn 3 chữ số thập phân.

## Sự kiện (events)
`mote_picked`, `deposit`, `lantern_lit`, `dash`, `charm_picked`, `pulse`,
`drifter_steal`, `player_hit`, `paused`, `resumed`, `game_over`.

## Luật thắng/thua
- Thắng: tất cả đèn thắp (`all lit`) → `game_over {result: won, reason: all_lit}`.
- Thua: hết 3 flames (Bóng Mực chạm) hoặc hết thời gian đêm → `game_over`.

## Tính tất định
Cùng `--seed`, cùng scenario, cùng inputs → output JSONL byte-identik giữa 2 lần chạy.
Kiểm chứng: `test_deterministic_output` + so hash mẫu ở `docs/proof/phase-2-evidence.md`.

## Exit code
- 0: thành công
- 1: lỗi chạy (chỉ hỗ trợ night 1/2/3; lỗi ghi output)
- 2: scenario/inputs sai định dạng
