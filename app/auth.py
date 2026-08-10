"""CP3 — Xác thực bằng API key.

Public URL = ai cũng gọi được. Không có lớp này, hóa đơn LLM của bạn do
người lạ quyết định.
"""

# Trì hoãn đánh giá type hint, giúp tương thích các kiểu union hiện đại.
from __future__ import annotations

# Cung cấp so sánh secret an toàn về thời gian thực hiện.
import secrets

# Header đọc giá trị từ request; HTTPException tạo response lỗi; status chứa mã chuẩn.
from fastapi import Header, HTTPException, status

# Lấy API key thật từ cấu hình environment/.env.
from .config import get_settings

# User mặc định khi request hợp lệ nhưng không có X-User-Id.
ANONYMOUS_USER = "anonymous"


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    """Kiểm tra header ``X-API-Key``; trả về user_id nếu hợp lệ.

    Header ``X-API-Key`` hợp lệ mới được phép đi tiếp tới ``/ask``.
    """
    # Đọc secret đã được validate trong Settings.
    # Settings đã fail-fast nếu AGENT_API_KEY thiếu hoặc là placeholder.
    expected_key = get_settings().agent_api_key
    # Dùng chuỗi rỗng khi header bị thiếu để compare_digest nhận hai chuỗi.
    # Chuyển None thành chuỗi rỗng để hai đối số luôn cùng kiểu str.
    provided_key = x_api_key or ""

    # So sánh constant-time để giảm nguy cơ timing attack.
    # compare_digest không dùng toán tử ==, giảm rủi ro timing attack.
    if not secrets.compare_digest(provided_key, expected_key):
        # Không phân biệt key thiếu và key sai trong thông báo trả về.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )

    # User ID là đơn vị rate limit và tính chi phí.
    # X-User-Id phục vụ rate limit/cost guard; thiếu thì gom vào anonymous.
    return x_user_id or ANONYMOUS_USER
