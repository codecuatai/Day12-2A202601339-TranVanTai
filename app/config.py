"""CP1 — Cấu hình theo 12-Factor.

Nguyên tắc: **không có giá trị cấu hình nào nằm trong code**. Tất cả đến từ
biến môi trường, để cùng một image chạy được ở laptop, staging và production
mà không phải sửa một dòng code nào.
"""

# Cho phép dùng kiểu dữ liệu hiện đại và trì hoãn việc đánh giá type hint.
from __future__ import annotations

# Cung cấp decorator để cache kết quả đọc cấu hình.
from functools import lru_cache

# Dùng để kiểm tra và chuẩn hóa giá trị trước khi Settings được tạo.
from pydantic import field_validator
# BaseSettings đọc dữ liệu từ environment; SettingsConfigDict cấu hình nguồn đọc.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toàn bộ cấu hình của service.

    pydantic-settings tự đọc biến môi trường theo tên trường (không phân biệt
    hoa thường), nên ``agent_api_key`` sẽ lấy giá trị từ ``AGENT_API_KEY``.

    | Trường                  | Kiểu  | Mặc định                   |
    |-------------------------|-------|----------------------------|
    | port                    | int   | 8000                       |
    | agent_api_key           | str   | KHÔNG có mặc định (bắt buộc)|
    | redis_url               | str   | "redis://localhost:6379/0" |
    | rate_limit_per_minute   | int   | 10                         |
    | monthly_budget_usd      | float | 10.0                       |
    | log_level               | str   | "INFO"                     |

    Vì sao ``agent_api_key`` không được có giá trị mặc định? Vì mặc định
    nghĩa là app vẫn khởi động khi bạn quên set secret trên cloud — và bạn
    chỉ phát hiện ra khi ai đó đã gọi API miễn phí bằng khóa mặc định đó.
    Không mặc định = fail fast ngay lúc khởi động.
    """

    # Cấu hình cách BaseSettings tìm và xử lý dữ liệu đầu vào.
    model_config = SettingsConfigDict(
        # Đọc thêm các giá trị từ file .env ở thư mục chạy ứng dụng.
        env_file=".env",
        # File .env được đọc bằng UTF-8 để hỗ trợ nội dung tiếng Việt.
        env_file_encoding="utf-8",
        # Bỏ qua các biến dư thừa trong .env thay vì báo lỗi.
        extra="ignore",
    )

    # Cổng HTTP: có thể ghi đè bằng biến môi trường PORT.
    # Khai báo kiểu int để chuỗi PORT từ environment được tự động chuyển thành số.
    port: int = 8000

    # Secret bắt buộc, không đặt giá trị mặc định để ứng dụng fail-fast
    # nếu môi trường chạy production chưa được cấu hình khóa thật.
    # Không có dấu "=" và giá trị mặc định: field này là bắt buộc.
    # Nếu thiếu AGENT_API_KEY, BaseSettings ném ValidationError ngay khi khởi tạo.
    agent_api_key: str

    # Các cấu hình còn lại có giá trị mặc định an toàn cho môi trường local.
    # URL Redis có thể được thay bằng REDIS_URL khi deploy production.
    redis_url: str = "redis://localhost:6379/0"
    # Số request tối đa mỗi phút cho mỗi user.
    rate_limit_per_minute: int = 10
    # Ngân sách LLM tối đa cho mỗi user trong một tháng, tính bằng USD.
    monthly_budget_usd: float = 10.0
    # Mức độ log mặc định; có thể ghi đè bằng LOG_LEVEL.
    log_level: str = "INFO"

    # Chạy validator sau khi Pydantic đã nhận giá trị agent_api_key.
    @field_validator("agent_api_key")
    # Cho phép validator được gọi trong ngữ cảnh class Settings.
    @classmethod
    def validate_agent_api_key(cls, value: str) -> str:
        """Chặn key rỗng hoặc key mẫu ngay khi ứng dụng khởi động."""
        # Loại bỏ khoảng trắng vô tình ở đầu/cuối giá trị secret.
        normalized = value.strip()

        # Những giá trị này chỉ là hướng dẫn trong .env.example, không được
        # dùng làm secret thật vì có thể khiến API bị truy cập trái phép.
        placeholders = {
            "changeme",
            "change-me",
            "your-api-key",
            "your_api_key",
            "doi-thanh-khoa-cua-rieng-ban",
        }
        # lower() giúp nhận diện cả Changeme, CHANGEME hoặc changeme.
        if not normalized or normalized.lower() in placeholders:
            # Pydantic sẽ chuyển lỗi này thành ValidationError (fail-fast).
            raise ValueError("AGENT_API_KEY must be a real, non-empty secret")

        # Trả về key đã loại bỏ khoảng trắng thừa ở đầu và cuối.
        return normalized


# Cache tối đa một Settings object để toàn app dùng cùng một cấu hình.
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Đọc cấu hình một lần rồi cache lại thay vì đọc env mỗi request."""
    # Lần gọi đầu tiên đọc .env/environment và chạy toàn bộ validation.
    # Các lần gọi sau trả lại object đã cache, giúp giảm chi phí xử lý.
    return Settings()
