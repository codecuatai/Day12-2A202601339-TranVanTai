"""CP1 — Structured logging.

`print("user abc hỏi gì đó")` là log cho người đọc. Cloud (Railway, Render,
Cloud Run, Datadog...) đọc log bằng máy: một dòng = một JSON object thì mới
lọc/đếm/cảnh báo được. Đây là khác biệt lớn giữa localhost và production.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """CHO SẴN — thời điểm hiện tại theo ISO-8601, múi giờ UTC."""
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, level: str = "info", **fields) -> str:
    """Ghi một dòng log JSON ra stdout.

    Mỗi event được chuyển thành một JSON object trên đúng một dòng để các
    hệ thống production có thể đọc, tìm kiếm và lọc tự động.

    Ví dụ:
        >>> log_event("ask_completed", user_id="sv01", cost_usd=0.0001)
        '{"event": "ask_completed", "level": "info", "timestamp": "...", ...}'
    """
    # Tạo bản ghi với các trường bắt buộc của structured log.
    record = {
        # Ghi thời điểm theo UTC để log giữa các server dùng cùng một múi giờ.
        "timestamp": utc_now_iso(),
        # Chuẩn hóa level về chữ thường để việc lọc log nhất quán.
        "level": level.lower(),
        # event mô tả hành động vừa xảy ra, ví dụ "ask_completed".
        "event": event,
    }

    # Gắn thêm các trường tùy chọn như user_id, latency_ms hoặc cost_usd.
    record.update(fields)

    # Chuyển dict thành JSON compact, không dùng indent để log chỉ có một dòng.
    # ensure_ascii=False giúp giữ nguyên tiếng Việt thay vì mã hóa thành \\uXXXX.
    raw = json.dumps(record, ensure_ascii=False)

    # In log ra stdout để Docker/cloud platform thu thập được log chuẩn.
    print(raw, file=sys.stdout)

    # Trả lại chuỗi JSON để code gọi hàm hoặc test có thể tiếp tục sử dụng.
    return raw
