# Nhật ký dùng AI — CP0

| Thời gian | Công cụ AI | Mục đích | Ước tính token | Ghi chú |
|-----------|------------|----------|----------------|---------|
| CP0 | Claude (agent này) | Tạo boilerplate CP0: README, AGENTS.md, hello_headless.py, test, cấu trúc thư mục | ~ | Tạo sẵn môi trường kiểm tra headless. |

## Cách tiết kiệm token
- Dùng model nhẹ cho việc định dạng file, tạo cấu trúc thư mục.
- Chỉ nhờ model mạnh khi thiết kế kiến trúc game sau khi đọc PRD-0.

## Lỗi AI đã phát hiện (CP0)
- Chưa có.

## Kế hoạch sau CP0
- Đăng nhập claude.ai, mở lab board, đọc PRD-0 Phase 1.
- Hỏi trợ giảng lab board một câu để xác nhận hoạt động.
- Clone repo sạch sang thư mục khác, chạy `python src/hello_headless.py` để Verify môi trường.