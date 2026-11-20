# ADR Phase 3 — Mô hình nhiên liệu đèn và thắng bình minh

- **Trạng thái:** Đã chọn
- **Ngày:** 2026-11-20
- **Bối cảnh:** Ticket-03 thay luật đèn chỉ có hai trạng thái bật/tắt không thể đảo ngược bằng mô hình nhiên liệu hao hụt, bị Bóng Mực hút, có thể châm dầu/thắp lại; đồng thời thay thắng sớm bằng giữ đảo sáng tới bình minh.

## Quyết định

1. Nhiên liệu được lưu nội bộ bằng số nguyên `fuel_60`; 60 đơn vị tương ứng 1.0 fuel. Mỗi tick hao 1 đơn vị; mỗi shade drain trừ thêm 5 đơn vị. Chỉ chuyển sang số thực một chữ số thập phân khi xuất JSONL. Khi chấm điểm bình minh dùng `fuel_60 // 60` để đúng `floor(fuel)`.
2. Trạng thái `lit` đồng bộ với `fuel_60 > 0`; khi hết fuel, đặt fuel về 0, tắt đèn, reset `deposited` về 0, giữ `ever_lit = true` và phát `lantern_out`.
3. Đèn scenario đặt `lit: true` mặc định fuel 100; không tính lần đặt sẵn vào `successful_lights`. `successful_lights` chỉ tăng do thắp mới/thắp lại bằng tương tác; capacity = `min(20, 10 + 2 * successful_lights)`.
4. Chỉ các shade ở `wander` chọn mục tiêu đèn; ưu tiên đèn sáng yếu nhất theo khoảng cách (tie-break ID), nếu không có thì chọn đèn tắt gần nhất. Shade `chase` giữ đích là người chơi. Drain là trạng thái đứng yên, thoát theo các điều kiện của ticket; pulse làm stunned, stun hết về wander.
5. Kết thúc chỉ xét sau toàn bộ cập nhật tick. `no_flames` ưu tiên hơn bình minh; khi hết thời gian, thắng nếu số đèn đang sáng đạt `ceil(0.6 * total)`, với lý do `dawn_survived`, nếu không thì `dawn`. Không còn thắng sớm/all_lit hay thưởng thời gian.

## Hệ quả

- Các test cũ kỳ vọng thắng ngay khi thắp đủ đèn phải được thay bằng test không thắng sớm và test thắng/thua ở bình minh; thay đổi được ghi chú tại `tests/test_phase_1.py` và `tests/test_phase_2.py`.
- Hiện repo chưa có GUI. Các yêu cầu trình bày như thanh nhiên liệu, nhấp nháy 1 Hz, viền/mắt đổi màu và ký hiệu cảnh báo không thể thể hiện trong engine headless; cần triển khai ở Phase 4 GUI. Chế độ mù màu được lưu trong config riêng, không làm đổi JSONL gameplay.
