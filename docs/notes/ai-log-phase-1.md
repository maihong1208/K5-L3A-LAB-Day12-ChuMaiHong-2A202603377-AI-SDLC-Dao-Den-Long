# Nhật ký dùng AI — Phase 1

| Thời gian | Công cụ AI | Mục đích | Ước tính token | Ghi chú |
|-----------|------------|----------|----------------|---------|
| Phase 1 | Claude (agent này) | Viết engine headless, test contract, assumptions, plan, evidence | ~ | Đã hoàn thành code và test 100% pass. |

## Cách tiết kiệm token
- Dùng Python stdlib (không cài thêm thư viện) để giảm thời gian thiết lập môi trường.
- Viết test trước, code sau để tránh viết lại nhiều lần.

## Lỗi AI đã phát hiện
- Motes trong scenario là list `[x,y,z]` không phải dict → đã sửa `_apply_scenario` để xử lý cả hai kiểu.
- `interact` là edge-triggered (false→true) → test phải bật/tắt tương tác, không để liên tiếp true.

## Kế hoạch
- Gắn tag `phase-1` và push lên repo cá nhân.
- Sang Phase 2 khi lab board phát hành Ticket-02.