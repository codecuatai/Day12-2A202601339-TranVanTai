"""CP3 — Rate limiting bằng thuật toán sliding window.

Đếm số request trong 60 giây **gần nhất** (cửa sổ trượt), thay vì đếm theo
phút đồng hồ. Đếm theo phút đồng hồ có lỗ hổng: 10 request lúc 10:00:59 và
10 request lúc 10:01:01 = 20 request trong 2 giây mà vẫn "đúng luật".

Cấu trúc dữ liệu: Redis Sorted Set (ZSET), score = timestamp của request.
"""

# Cho phép dùng type hint kiểu ``float | None`` trên Python hiện đại.
from __future__ import annotations

# Lấy timestamp request hiện tại.
import time
# Tạo member duy nhất cho Redis Sorted Set.
import uuid

# HTTPException trả 429; status cung cấp tên mã HTTP dễ đọc.
from fastapi import HTTPException, status

# Một request chỉ được tính trong 60 giây gần nhất.
WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, client, limit_per_minute: int) -> None:
        # Redis client là nơi lưu quota dùng chung giữa nhiều container.
        self.client = client
        # Hạn mức được đọc từ cấu hình và truyền vào provider.
        self.limit = limit_per_minute

    @staticmethod
    def _key(user_id: str) -> str:
        """CHO SẴN — mỗi user một key riêng."""
        return f"ratelimit:{user_id}"

    def hit_count(self, user_id: str, now: float | None = None) -> int:
        """Số request của user trong ``WINDOW_SECONDS`` giây gần nhất.

        Redis Sorted Set dùng timestamp làm score để xóa theo thời gian.
        """
        # Cho phép test truyền thời gian cố định; runtime dùng thời gian hiện tại.
        now = now if now is not None else time.time()
        key = self._key(user_id)

        # Xóa các request đã nằm ngoài cửa sổ 60 giây.
        self.client.zremrangebyscore(key, 0, now - WINDOW_SECONDS)

        # Số phần tử còn lại là số request trong cửa sổ hiện tại.
        return int(self.client.zcard(key))

    def check(self, user_id: str, now: float | None = None) -> None:
        """Cho qua nếu còn quota, ngược lại raise 429.

        Kiểm tra trước, chỉ ghi nhận request sau khi còn quota.
        """
        # Dùng cùng một mốc thời gian cho prune, count và record.
        now = now if now is not None else time.time()
        count = self.hit_count(user_id, now)

        # Request bị chặn không được ghi vào quota.
        if count >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )

        # UUID bảo đảm member duy nhất khi hai request có cùng timestamp.
        key = self._key(user_id)
        self.client.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})

        # Cho Redis tự dọn key sau khi không có request mới.
        self.client.expire(key, WINDOW_SECONDS)
