# Đảo Đèn Lồng — AI SDLC Lab (K5-L3A-Day12)

> Game 3D góc nhìn thứ ba: người giữ đèn nhỏ tuổi gom đom đóm để thắp lại các Đèn Lồng Lớn và né Bóng Mực trong sương đen.

🎥 **Video demo:** [link video ở đây, dưới 5 phút] — sẽ cập nhật sau Phase 4.

## Cài đặt & chạy (tối đa 3 lệnh)

```bash
# 1. Clone repo
git clone https://github.com/maihong1208/K5-L3-LAB-Day12-ChuMaiHong-2A202603377-AI-SDLC-Dao-Den-Long.git && cd K5-L3-LAB-Day12-ChuMaiHong-2A202603377-AI-SDLC-Dao-Den-Long

# 2. Chạy kiểm tra môi trường headless
python src/hello_headless.py

# 3. Chạy test
python -m pytest tests/
```

## Điều khiển
- Chưa xác định (cập nhật sau khi đọc PRD-0 Phase 1 và chọn engine).

## Chế độ headless & Test Contract
- `python src/hello_headless.py` in ra trạng thái JSON (không cần cửa sổ đồ họa).
- Test Contract chi tiết của mỗi phase nằm trên lab board (claude.ai) và sẽ được cập nhật vào đây.

## Cách chạy kiểm chứng của riêng bạn
```bash
python -m pytest tests/
```

## Sáng tạo của tôi
- Chưa có. Sẽ ghi vào mục này sau khi hoàn thành, đảm bảo không phá yêu cầu/Test Contract.

## Harness AI
- Xem `AGENTS.md`.

## Ghi chép
- `docs/notes/assumptions-phase-0.md`: giả định CP0.
- `docs/notes/ai-log-phase-0.md`: nhật ký AI CP0.
- `docs/notes/assumptions-phase-1.md`: giả định Phase 1 (dựa trên PRD-0).
- `docs/notes/plan-phase-1.md`: kế hoạch Phase 1.
- `docs/notes/test-contract-phase-1.md`: Test Contract Phase 1 (v1.0).
- `docs/proof/phase-1-evidence.md`: bằng chứng Phase 1 (12/12 test pass).
- `docs/proof/phase-1-headless-sample.jsonl`: mẫu đầu ra headless.

## CREDITS & LICENSE
- Xem `CREDITS.md` và `LICENSE`.

--- 
*Repo public. Không commit .env, API key, token.*