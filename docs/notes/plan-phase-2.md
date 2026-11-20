# Kế hoạch Phase 2 — Ticket-02 / Test Contract v1.1

## Mục tiêu
Mở rộng engine Phase 1 thành 3 đêm, giữ deterministic/headless, bổ sung dash, charm và
các entity mới theo contract mà không làm hỏng hành vi cũ còn hiệu lực.

## Kế hoạch kiểm chứng
1. Chạy toàn bộ `python -m pytest tests/` sau tích hợp; duy trì test Phase 0/1 và thêm test Phase 2.
2. Bao phủ: cấu trúc snapshot/end; deterministic với seed/scenario/inputs; 5/6/7 đèn theo đêm;
   di chuyển; nhặt mote; nạp đèn/thắng; dash; nhặt charm; snapshot interval.
3. Chạy headless trên night 2 với seed cố định, lưu JSONL; chạy lại cùng lệnh và so byte đầu ra.
4. Chạy `python src/hello_headless.py` để kiểm tra CP0 không hồi quy.
5. Ghi rõ trong assumptions các quyết định ở điểm mơ hồ; cập nhật test Phase 1 theo contract v1.1,
   không tắt test âm thầm.

## Kết quả triển khai
- Đã phát hiện/sửa snapshot bị phát dư trong `step()`, mote ban đầu chưa spawn dù tuning khai báo 20,
  và tốc độ flee của Drifter bị nhân đôi.
- Test Phase 1 dùng đường dẫn tuyệt đối cũ được chuyển sang đường dẫn tương đối theo repo.
- Kết quả chi tiết và lệnh tái tạo ở `docs/proof/phase-2-evidence.md`.
