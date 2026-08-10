# Thông Tin Deploy — Checkpoint 5

> Điền file này sau khi deploy xong. `pytest tests/test_cp5.py` đọc file này
> để tìm địa chỉ service của bạn và gọi thử.
>
> **Chỉ ghi TÊN biến môi trường, tuyệt đối không dán giá trị API key vào đây.**
> Repo này công khai — dán khóa vào là mất khóa.

## Thông Tin Học Viên

| Mục | Nội dung |
|-----|----------|
| Họ và tên | Trần Văn Tài |
| Mã học viên | 2A202601339 |
| Repo | https://github.com/codecuatai/Day12-2A202601339-TranVanTai |

## Service

| Mục | Nội dung |
|-----|----------|
| Public URL | https://day12-agent-production-3b14.up.railway.app |
| Platform | Railway |
| Ngày deploy | 2026-08-10 |

## Biến Môi Trường Đã Set Trên Cloud

Ghi tên biến và **nguồn giá trị**, không ghi giá trị:

| Biến | Đã set | Ghi chú |
|------|--------|---------|
| `PORT` | Đã set tự động | Railway tự gán |
| `AGENT_API_KEY` | Đã set | đặt trong dashboard, không nằm trong repo |
| `REDIS_URL` | Đã set | reference tới Redis service `day12-redis` |
| `RATE_LIMIT_PER_MINUTE` | Đã set | 10 |
| `MONTHLY_BUDGET_USD` | Đã set | 10.0 |
| `LOG_LEVEL` | Đã set | INFO |

## Lệnh Kiểm Tra

Public URL dùng để kiểm tra:

```bash
# 1. Liveness — mong đợi 200 {"status":"ok"}
curl -i https://day12-agent-production-3b14.up.railway.app/health

# 2. Readiness — mong đợi 200 {"status":"ready"} (đã nối được Redis)
curl -i https://day12-agent-production-3b14.up.railway.app/ready

# 3. Không có API key — mong đợi 401
curl -i -X POST https://day12-agent-production-3b14.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

# 4. Có API key — mong đợi 200 kèm câu trả lời
curl -i -X POST https://day12-agent-production-3b14.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "X-User-Id: sv-test" \
  -d '{"question":"Deploy là gì?"}'

# 5. Rate limit — gọi 15 lần, những lần cuối phải trả 429
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST https://day12-agent-production-3b14.up.railway.app/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "X-User-Id: sv-test" \
    -d '{"question":"test"}'
done; echo
```

## Kết Quả Chạy Thật

Dán output của các lệnh trên vào đây:

```
GET /health → HTTP 200
{"status":"ok","service":"day12-agent","version":"1.0.0"}

GET /ready → HTTP 200
{"status":"ready","redis":true}

POST /ask không có API key → HTTP 401
{"detail":"invalid or missing API key"}

POST /ask có API key thật → HTTP 200
Response có `user_id: "cp5-test"`, `history_length: 0`, `cost_usd: 2.265e-05`.
```

## Ảnh Chụp Màn Hình

Đặt ảnh trong thư mục `screenshots/`:

- `screenshots/image.png` — dashboard Railway hiển thị deployment thành công
- `screenshots/health.png` — cần chụp kết quả gọi các endpoint live

---

## Nếu Dùng Phương Án Dự Phòng

Không đăng ký được tài khoản cloud? Vẫn nộp được bài, nhưng CP5 tối đa 60% điểm:

1. Đặt `LOCAL_FALLBACK=true` trong `.env`
2. Chạy `docker compose up -d` rồi kiểm tra `docker compose ps`
3. Chụp màn hình vào `screenshots/`
4. Chạy `pytest tests/test_cp5.py -v` — bộ test sẽ tự chuyển sang kiểm tra
   `http://localhost:8000`
5. Ghi rõ lý do không deploy được vào phần dưới đây:

```
Không dùng local fallback; đang chờ deploy Railway.
```
