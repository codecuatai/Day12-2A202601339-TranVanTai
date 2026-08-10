# Phiếu Phản Ánh — K3 Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng `> *Câu trả lời của bạn*` bằng câu trả lời.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Trần Văn Tài  Mã học viên: 2A202601339

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Nếu deploy lên cloud mà quên cấu hình `AGENT_API_KEY`, `Settings` không có giá
trị mặc định cho trường này nên Pydantic sẽ tạo `ValidationError` ngay khi
ứng dụng khởi động. Trong code hiện tại, validator còn chặn key rỗng và các
placeholder như `changeme`. Nhờ vậy container dừng ngay thay vì chạy bằng một
khóa ai cũng đoán được. Nếu để mặc định `changeme`, container có thể báo
healthy, nhận request thật và người lạ có thể gọi API hoặc làm phát sinh chi
phí trước khi phát hiện cấu hình secret bị thiếu.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Mình đã chạy trực tiếp hàm `log_event()` trong code và thu được một dòng JSON:

```text
{"timestamp": "2026-08-10T03:45:03.549657+00:00", "level": "info", "event": "ask_completed", "user_id": "sv01", "latency_ms": 142}
```

Lưu ý: mình chưa thể lấy log từ việc gọi `/ask` thật vì endpoint `/ask` vẫn là
TODO của CP3 và Uvicorn còn bị chặn bởi `lifecycle.install()` của CP4. Dòng
trên là kết quả chạy thật của chính `log_event()`.

Với dòng log có cấu trúc này, mình có thể:

1. Lọc tất cả event `ask_completed` của `user_id=sv01` mà không cần đọc chuỗi
   tự do bằng mắt.
2. Tính hoặc cảnh báo theo các trường có kiểu rõ ràng như `latency_ms`, ví dụ
   tìm các request có latency lớn hơn 500 ms.

`print("đã trả lời xong")` không chứa tên event, user ID hoặc latency nên không
thể lọc và thống kê chính xác như vậy.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | Chưa đo được — Docker Hub trả lỗi 429 khi kéo `python:3.11` |
| Multi-stage | 270 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Mình đã build thật image multi-stage bằng lệnh `docker build -t
day12-agent:prod .` và đo được `270 MB`. Khi thử build bản 1-stage tương ứng
với Dockerfile ban đầu, Docker Hub trả:

```text
unexpected status from HEAD request to https://registry-1.docker.io/v2/library/python/manifests/3.11: 429 Too Many Requests
```

Vì bản 1-stage chưa build thành công nên mình không điền một con số phỏng
đoán cho nó. Phần chênh lệch kỳ vọng đến từ việc bản 1-stage giữ cả base image
đầy đủ, pip cache, dependencies và toàn bộ build context trong cùng image;
bản multi-stage chỉ copy dependencies đã cài và source cần chạy sang image
`python:3.11-slim` production.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

Trong Dockerfile hiện tại, `COPY requirements.txt .` đứng trước
`RUN pip install ...`, còn `COPY app/ app/` và `COPY utils/ utils/` đứng sau.
Vì vậy khi chỉ sửa một dòng trong `app/main.py`, Docker có thể dùng lại:

- layer lấy `python:3.11-slim`;
- `WORKDIR /build`;
- `COPY requirements.txt .`;
- layer `pip install`;
- các layer trước phần source bị thay đổi.

Từ layer `COPY app/ app/` trở đi, các layer runtime phía sau có thể phải tạo
lại vì nội dung source đã thay đổi. Dependencies không cần cài lại. Nếu đặt
`COPY . .` trước `RUN pip install`, chỉ một thay đổi nhỏ trong source cũng làm
layer `COPY . .` thay đổi, khiến Docker phải chạy lại `pip install`; build sẽ
chậm hơn và mất lợi ích của cache dependency.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

Nếu container chạy bằng root và ứng dụng có lỗ hổng cho phép kẻ tấn công thực
thi mã lệnh, process bị khai thác sẽ có quyền root bên trong container. Từ đó
kẻ tấn công có thể đọc hoặc sửa nhiều file hơn, khai thác quyền của Docker
socket nếu socket bị mount, hoặc tìm cách leo thang sang host tùy cấu hình
container.

Trong Dockerfile, lệnh:

```dockerfile
RUN adduser --disabled-login --no-create-home --gecos "" appuser
USER appuser
```

chuyển process runtime sang user thường. Vì vậy ngay cả khi code bị khai thác,
quyền ban đầu của process bị giới hạn, cắt đứt bước leo thang trực tiếp từ
ứng dụng thành root trong container.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

Nếu hạn mức là 10 request/phút nhưng dùng fixed window reset ở giây 00, user
có thể gửi tối đa **20 request trong khoảng 2 giây**. Cụ thể, gửi 10 request
ở `10:00:59`, ngay trước khi cửa sổ cũ kết thúc, rồi gửi thêm 10 request ở
`10:01:00` hoặc `10:01:01`, sau khi bộ đếm đã reset. Hai nhóm đều được chấp
nhận vì rơi vào hai phút khác nhau, dù thực tế xảy ra gần như liên tiếp.

Sliding window trong `app/rate_limiter.py` tránh lỗi này bằng cách lưu timestamp
từng request trong Redis Sorted Set, xóa request cũ hơn 60 giây rồi mới đếm.
Test CP3 kiểm tra rằng request trong cùng cửa sổ bị trả 429 và được gọi lại
sau khi request cũ ra khỏi cửa sổ.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

Rate limit bảo vệ hạ tầng bằng cách giới hạn **tốc độ/số lượng request** trong
60 giây. Cost guard bảo vệ ngân sách bằng cách cộng dồn **chi phí USD theo user
và theo tháng** trong Redis.

Ví dụ rate limit cho qua nhưng cost guard chặn: user chỉ gửi 1 request mỗi
phút nên không vượt hạn mức 10 request/phút, nhưng trước request mới đã tiêu
`10.20 USD` trong tháng trong khi budget là `10.00 USD`. `guard.check()` sẽ
trả lỗi `402 Payment Required` trước khi gọi LLM.

Ví dụ cost guard còn cho qua nhưng rate limit chặn: user gửi 4 request liên
tiếp trong một phút, mỗi request chỉ tốn một khoản rất nhỏ và tổng chi phí
vẫn dưới `10.00 USD`, nhưng rate limit đang là 3 request/phút. Request thứ tư
sẽ bị trả `429 Too Many Requests`.

Kết quả chạy thực tế của `pytest tests/test_cp3.py -q` là:

```text
22 passed in 0.61s
```

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Nếu gộp hai endpoint và endpoint đó kiểm tra Redis, khi Redis mất kết nối thì
cả 3 container đều báo unhealthy. Orchestrator có thể restart cả 3 container
cùng lúc. Trong 30 giây Redis lỗi, các container mới cũng không kết nối được
Redis nên tiếp tục bị restart; khi Redis hoạt động lại thì cụm có thể không còn
instance sẵn sàng phục vụ. Tách endpoint giúp `/health` chỉ kiểm tra process,
còn `/ready` báo 503 để load balancer ngừng gửi traffic mà không restart oan
container.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

Mình đã chạy Compose với 3 agent replicas và gọi qua Nginx bằng cùng một
`X-User-Id`. Kết quả thực tế là:

```text
request=1 history_length=0
request=2 history_length=2
request=3 history_length=4
request=4 history_length=6
request=5 history_length=8
```

Ngoài ra, `docker compose ps` cho thấy cả 3 agent và Redis đều ở trạng thái
`healthy`, `/health` trả `status=ok`, `/ready` trả `status=ready, redis=true`.

Nếu lưu history trong một dict Python, mỗi container sẽ có một dict riêng.
Request rơi vào container mới hoặc container chưa có history có thể lại thấy
`history_length=0` (sau đó tăng riêng trong container đó), nên kết quả sẽ nhảy
hoặc reset tùy Nginx điều phối request. Lưu Redis giúp cả 3 container thấy cùng
một danh sách history dùng chung.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

> *Câu trả lời của bạn*
