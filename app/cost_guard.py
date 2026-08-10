"""CP3 — Cost guard: chặn chi phí trước khi hóa đơn chặn bạn.

Rate limit giới hạn *số lượng* request. Cost guard giới hạn *số tiền*: một
user gửi 10 request/phút nhưng mỗi request 50k token vẫn đốt sạch ngân sách.
"""

# Cho phép dùng union type trong chữ ký hàm.
from __future__ import annotations

# Lấy tháng hiện tại theo UTC để mọi instance dùng cùng nhãn tháng.
from datetime import datetime, timezone

# HTTPException trả 402; status cung cấp mã HTTP có tên rõ nghĩa.
from fastapi import HTTPException, status

# Giữ dữ liệu chi tiêu khoảng 40 ngày để còn đối soát sang tháng sau.
KEY_TTL_SECONDS = 40 * 24 * 3600


class CostGuard:
    def __init__(self, client, monthly_budget_usd: float) -> None:
        # Redis lưu tổng chi phí dùng chung giữa các instance.
        self.client = client
        # Budget tối đa của một user trong một tháng.
        self.budget = monthly_budget_usd

    @staticmethod
    def current_month() -> str:
        """CHO SẴN — nhãn tháng hiện tại dạng '2026-08' (UTC)."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @classmethod
    def _key(cls, user_id: str, month: str | None = None) -> str:
        """CHO SẴN — khóa Redis theo từng user, từng tháng."""
        return f"cost:{user_id}:{month or cls.current_month()}"

    def spent(self, user_id: str, month: str | None = None) -> float:
        """Số tiền user đã tiêu trong tháng.

        Key chưa tồn tại được coi là tổng chi phí bằng 0.
        """
        # Redis trả None khi user chưa có chi phí trong tháng.
        value = self.client.get(self._key(user_id, month))
        if value is None:
            return 0.0
        # Redis thường trả chuỗi, nên chuẩn hóa thành float.
        return float(value)

    def check(
        self,
        user_id: str,
        estimated_cost: float = 0.0,
        month: str | None = None,
    ) -> None:
        """Cho qua nếu còn ngân sách, ngược lại raise 402.

        Đây là pre-check: chặn trước khi gọi LLM nếu đã vượt ngân sách.
        """
        # Chặn trước khi gọi LLM nếu chi phí dự kiến vượt budget.
        if self.spent(user_id, month) + estimated_cost > self.budget:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="monthly budget exceeded",
            )

    def record(self, user_id: str, cost: float, month: str | None = None) -> float:
        """Cộng dồn chi phí vừa phát sinh, trả về tổng mới.

        Đây là post-record: cộng chi phí thực tế sau khi LLM trả kết quả.
        """
        # Redis thực hiện cộng dồn ở server để các instance dùng chung tổng.
        key = self._key(user_id, month)
        total = self.client.incrbyfloat(key, cost)
        # Giữ dữ liệu khoảng 40 ngày để đối soát rồi tự dọn.
        self.client.expire(key, KEY_TTL_SECONDS)
        return float(total)
