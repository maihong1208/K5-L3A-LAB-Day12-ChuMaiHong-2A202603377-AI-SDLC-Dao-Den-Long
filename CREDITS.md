# CREDITS

## Nhân vật, bối cảnh, tên gọi
- Bản gốc của lab **Đảo Đèn Lồng** (K5-L3-LAB-Day12). Không dùng nhân vật,
  nhạc, mô hình 3D hay thương hiệu của game/phim có sẵn.

## Asset bên ngoài
- **Không có.** Mọi hình ảnh, sprite và hiệu ứng trong game đều tạo thủ tục
  (procedural) bằng code: hình chiếu phối cảnh 3D từ sprite 2D, glow radial,
  mây, đom đóm, Bóng Mực... Âm thanh: chưa có (không bắt buộc theo lab).
- Thư viện mã nguồn mở (GPL/MIT): `pygame-ce` (giao diện + hiển thị SDL2),
  `psutil` (đo bộ nhớ), `imageio-ffmpeg` (nhúng ffmpeg để xuất video demo).

## Công cụ AI tạo nội dung
- **Claude Code (harness AI)** được dùng làm "AI Agent" cho toàn bộ SDLC:
  đọc ticket, lập kế hoạch, viết engine headless, test, GUI, benchmark, soak,
  bảng xếp hạng, tài liệu. Đây là công cụ chính chứng minh "đi theo AI SDLC".
- Nội dung code/ghi chú trong `docs/notes/ai-log-phase-*.md` là nhật ký của
  quá trình dùng AI Agent. (Không dùng AI để vẽ tranh, tạo nhạc.)

## Ghi chú trung thực
- Video demo `.mp4` (docs/demo/) được sinh tự động bằng ffmpeg (imageio-ffmpeg)
  từ các khung hình của chế độ benchmark; không phải quay thủ công.

## Tham khảo
- [Lab board: Đảo Đèn Lồng Lab](https://claude.ai/artifact/Q1RYyv1dxjUczzCbd2ZnoW)
