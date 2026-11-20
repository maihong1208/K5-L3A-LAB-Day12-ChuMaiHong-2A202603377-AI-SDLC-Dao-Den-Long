# Giả định Phase 2 (Ticket-02 + Test Contract v1.1)

## Source of truth
- `game.contract.json` (contract_version 1.1) là tuning chuẩn; `src/game_headless.py`
  phải khớp. Mọi con số trong TUNING của engine lấy từ contract.
- Đêm 1: 5 đèn, đêm 2: 6 đèn, đêm 3: 7 đèn (vị trí cứng theo đêm, không theo seed).

## Giả định game (nơi ticket/PRD còn mơ hồ)
- `motes_initial = 20` đom đóm ban đầu, vị trí ngẫu nhiên theo seed (bán kính 5–35 m),
  cùng bộ `random.Random(seed)` với toàn bộ mô phỏng → deterministic.
- `motes_cap = 30`, spawn định kỳ mỗi 240 tick (4 s) quanh gốc bán kính 5–35 m.
- Đom đóm rơi sau khi bị Bóng Mực tát: `ttl_s = 8`, loại `dropped`, rải bán kính 1.5–2.5 m.
- Bóng Mực: đêm 1 sinh 2 con tại tick 300 (bán kính 37 m), tối đa 6; đêm 2: 0 ban đầu,
  tối đa 8, bán kính 26 m; đêm 3: tối đa 10, bán kính 43 m; chu kỳ spawn 480/420/360 tick.
- Gió Lạc: tối đa 2, spawn tại tick 1200, 2400, ...; đuổi khi người chơi mang ≥ 5 đom
  đóm trong 15 m; cướp 3 đom khi chạm (bán kính 1.2 m) rồi bỏ chạy 240 tick.
- Bùa Gió: không tự sinh trong mô phỏng (chỉ qua `--scenario`); hiệu lực 600 tick
  (10 s), respawn 2700 tick; tốc chạy khi có bùa 7.2 m/s.
- Wind (gió) trong snapshot: field khai báo theo contract v1.1 nhưng chưa có động lực
  wind ở Phase 2 (`active: false`), để Phase 3/4 quyết định.
- Chìm dưới -10 m: chưa xử lý (đảo phẳng ở Phase 2, `fall_enabled` giữ false từ Phase 1).

## Giả định điều khiển (GUI thuộc Phase 4, engine chỉ đọc inputs)
- Di chuyển: WASD / mũi tên (vector `move`, camera yaw = `cam_yaw_deg`).
- `interact` = E: nhặt đom đóm / nạp đèn.
- `jump` = Space, `dash` = Shift, `pulse` = Q, `pause` = P.
- Input edge-triggered: chỉ xử lý cạnh false→true (pause, jump, dash, pulse, interact).

## Thay đổi so với Phase 1 (v1.0 → v1.1)
- `lantern_cost`: 1 → 10 (đúng contract v1.1) — 2 test Phase 1 phải cập nhật scenario
  (ghi trong commit + comment test).
- Snapshot: bỏ field `motes_active`, thêm `motes`, `drifters`, `charms`, `wind`,
  các trường player mới (`vel`, `grounded`, `invuln`, `dash_cd_s`, `pulse_cd_s`, `charm_s`).
- `pulse` tốn 3 đom (Phase 1: 0) + cooldown 3 s.
