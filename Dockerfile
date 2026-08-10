# CP2 — Multi-stage production image.
# Docker sẽ đọc file này từ trên xuống dưới và tạo ra image cuối cùng.

# Stage 1 chỉ dùng để cài dependencies; các công cụ build không đi vào runtime.
# `FROM` chọn image nền; `AS builder` đặt tên cho stage để stage sau tham chiếu.
FROM python:3.11-slim AS builder

# Đặt thư mục làm việc mặc định cho các lệnh tiếp theo trong stage builder.
WORKDIR /build

# Copy riêng requirements để Docker giữ cache khi chỉ sửa source code.
# Chỉ file dependency được copy ở layer này, nên sửa app/ không làm mất layer pip.
COPY requirements.txt .

# Cài package vào thư mục trung gian, không lưu pip cache.
# `--prefix=/install` đặt package vào thư mục để copy sang stage production.
# `--no-cache-dir` giảm kích thước layer bằng cách không giữ file cache pip.
# `--root-user-action=ignore` tránh cảnh báo khi builder cài package bằng root.
RUN pip install --no-cache-dir --root-user-action=ignore --prefix=/install -r requirements.txt

# Stage 2 là image production tối giản.
# Stage mới không thừa hưởng filesystem build ngoài những gì ta COPY rõ ràng.
FROM python:3.11-slim

# Các lệnh COPY/CMD sau đó sẽ thực hiện tương đối với /app.
WORKDIR /app

# Chỉ copy dependencies đã cài từ builder sang runtime image.
# Không copy compiler, pip cache hoặc thư mục /build của stage builder.
COPY --from=builder /install /usr/local

# Chỉ đưa source cần thiết vào image, không copy .env, test hoặc git history.
# `.dockerignore` loại các file nhạy cảm trước khi Docker tạo build context.
COPY app/ app/
COPY utils/ utils/

# Tạo user thường để giảm tác động nếu ứng dụng bị khai thác.
# Tạo user không cho đăng nhập trực tiếp và không tạo home directory.
# `--gecos ""` giúp lệnh chạy non-interactive trong quá trình build.
RUN adduser --disabled-login --no-create-home --gecos "" appuser
# Từ dòng này, container runtime chạy dưới appuser thay vì root.
USER appuser

# Document cổng mà Uvicorn phục vụ bên trong container.
# Đây không phải mapping cổng host; mapping được khai báo ở Compose/Nginx.
EXPOSE 8000

# Healthcheck dùng Python vì python:slim không đảm bảo có curl.
# PORT được đọc động để tương thích môi trường cloud.
# Docker đánh container unhealthy nếu lệnh này lỗi 3 lần liên tiếp.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3)"

# Dùng shell để ${PORT:-8000} được expand khi container khởi động.
# `exec` chuyển process Uvicorn thành PID 1 để nhận signal shutdown đúng cách.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
