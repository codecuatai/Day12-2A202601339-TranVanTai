"""CP4 — Stateless: state sống ngoài process.

Nếu lịch sử hội thoại nằm trong một dict trong RAM, thì khi scale lên 3
instance, user hỏi câu 1 vào instance A và câu 2 vào instance B sẽ thấy agent
"mất trí nhớ". Container còn bị restart bất cứ lúc nào. Vì vậy state phải
nằm ở nơi mọi instance cùng nhìn thấy: Redis.
"""

# Cho phép dùng kiểu list[dict] và union type hiện đại.
from __future__ import annotations

# Serialize message thành JSON trước khi lưu vào Redis.
import json

# Redis client thật dùng khi chạy Docker/production.
import redis

from .config import get_settings

# Giới hạn prompt ở 20 message gần nhất.
HISTORY_MAX_MESSAGES = 20
# Xóa hội thoại không hoạt động sau 7 ngày.
HISTORY_TTL_SECONDS = 7 * 24 * 3600


def get_redis_client(url: str | None = None):
    """CHO SẴN — tạo client Redis từ URL.

    ``fake://`` trả về Redis giả chạy trong RAM, dùng khi máy bạn chưa có
    Docker. Tiện cho lúc học, nhưng KHÔNG dùng khi deploy: nó vẫn là state
    trong process, đúng cái mà CP4 đang tìm cách loại bỏ.
    """
    # Ưu tiên URL truyền trực tiếp; nếu không thì đọc từ Settings.
    url = url or get_settings().redis_url
    if url.startswith("fake://"):
        # FakeRedis giúp test/local chạy không cần Docker Redis.
        import fakeredis

        # decode_responses=True để Redis trả str thay vì bytes.
        return fakeredis.FakeRedis(decode_responses=True)
    # redis.from_url tạo client thật từ redis:// URL.
    return redis.from_url(url, decode_responses=True)


class ConversationStore:
    """Lưu lịch sử hội thoại của từng user trong Redis List."""

    def __init__(self, client) -> None:
        # Store không giữ history trong RAM; chỉ giữ client Redis.
        self.client = client

    @staticmethod
    def _key(user_id: str) -> str:
        """CHO SẴN."""
        return f"history:{user_id}"

    def ping(self) -> bool:
        """Redis có trả lời không? Dùng cho endpoint /ready.

        Trả ``True`` nếu Redis phản hồi thành công, ``False`` nếu có lỗi
        kết nối như mất mạng, sai mật khẩu hoặc Redis chưa khởi động.
        """
        try:
            # Redis client phản hồi khi server còn kết nối được.
            self.client.ping()
            return True
        except Exception:
            # Readiness không được làm app crash chỉ vì dependency tạm thời lỗi.
            return False

    def append(self, user_id: str, role: str, content: str) -> None:
        """Ghi thêm một lượt vào lịch sử.

        TODO (CP4):
          1. ``self.client.rpush(key, json.dumps({"role": role, "content": content},
             ensure_ascii=False))``
          2. ``self.client.ltrim(key, -HISTORY_MAX_MESSAGES, -1)`` — chỉ giữ
             ``HISTORY_MAX_MESSAGES`` message gần nhất, nếu không prompt sẽ
             phình vô hạn và tiền token cũng vậy.
          3. ``self.client.expire(key, HISTORY_TTL_SECONDS)`` — hội thoại cũ
             tự hết hạn, khỏi phải dọn tay.
        """
        # Key riêng cho từng user giúp cô lập lịch sử hội thoại.
        key = self._key(user_id)
        # Lưu role và content trong một JSON string của Redis List.
        message = json.dumps(
            {"role": role, "content": content},
            ensure_ascii=False,
        )
        # RPUSH thêm message vào cuối list, giữ thứ tự hội thoại.
        self.client.rpush(key, message)
        # Chỉ giữ N message mới nhất để prompt không phình vô hạn.
        # LTRIM giữ N phần tử cuối, tức các message mới nhất.
        self.client.ltrim(key, -HISTORY_MAX_MESSAGES, -1)
        # Hội thoại cũ tự hết hạn sau 7 ngày kể từ lượt cuối.
        # TTL giúp Redis tự dọn state cũ, tránh bộ nhớ tăng vô hạn.
        self.client.expire(key, HISTORY_TTL_SECONDS)

    def get_history(self, user_id: str) -> list[dict]:
        """Đọc lịch sử hội thoại, cũ nhất trước.

        TODO (CP4): ``self.client.lrange(key, 0, -1)`` rồi ``json.loads``
        từng phần tử. Chưa có gì → trả về list rỗng.
        """
        # Redis List giữ thứ tự từ message cũ nhất đến mới nhất.
        # LRANGE lấy từ phần tử đầu tới cuối, cũ nhất trước mới nhất sau.
        entries = self.client.lrange(self._key(user_id), 0, -1)
        # Giải mã từng JSON string về dictionary Python.
        # Decode từng JSON entry thành dict để mock LLM sử dụng.
        return [json.loads(entry) for entry in entries]

    def clear(self, user_id: str) -> None:
        """CHO SẴN — xóa lịch sử của một user."""
        self.client.delete(self._key(user_id))
