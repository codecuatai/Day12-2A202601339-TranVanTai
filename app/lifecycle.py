"""CP4 — Graceful shutdown.

Khi bạn deploy phiên bản mới, orchestrator (Docker, Railway, Cloud Run, K8s)
gửi **SIGTERM** rồi đợi vài chục giây trước khi SIGKILL. Nếu app bỏ qua tín
hiệu đó, mọi request đang xử lý dở bị cắt giữa chừng — user thấy lỗi 502 mỗi
lần bạn deploy.

Ứng xử đúng: nhận SIGTERM → báo "tôi sắp tắt" qua health check để load
balancer ngừng đẩy traffic mới vào → xử lý nốt request đang chạy → thoát.
"""

# Cho phép dùng type hint hiện đại mà không đánh giá sớm.
from __future__ import annotations

# Module chuẩn của Python để nhận SIGTERM/SIGINT.
import signal


class Lifecycle:
    """Giữ trạng thái vòng đời của process."""

    def __init__(self) -> None:
        # Cờ này được health/readiness endpoint đọc để trả 503 khi shutdown.
        self.shutting_down = False
        # Handler đã được đăng ký trước ta (của uvicorn) — xem install()
        self._previous: dict = {}

    def request_shutdown(self, signum=None, frame=None) -> None:
        """Signal handler: đánh dấu process đang tắt dần.

        TODO (CP4):
          1. ``self.shutting_down = True``
          2. Gọi lại handler cũ nếu có::

                previous = self._previous.get(signum)
                if callable(previous):
                    previous(signum, frame)

        Bước 2 quan trọng hơn vẻ ngoài của nó. Mỗi tín hiệu chỉ có **một**
        handler: đăng ký handler của mình là ghi đè handler của uvicorn — thứ
        chịu trách nhiệm thật sự cho việc dừng server. Không gọi lại nó thì
        app bật cờ "đang tắt" rồi... chạy tiếp mãi mãi, cho tới khi
        orchestrator hết kiên nhẫn và SIGKILL. Đúng cái mà graceful shutdown
        định tránh.

        Chữ ký ``(signum, frame)`` là bắt buộc vì Python gọi handler với 2
        tham số này. Không làm gì nặng ở đây (không gọi mạng, không ghi file)
        — handler chạy xen giữa bytecode.
        """
        # Signal handler chỉ bật cờ, không thực hiện I/O hoặc công việc nặng.
        self.shutting_down = True

        # Handler của Lifecycle đã ghi đè handler cũ của Uvicorn.
        previous = self._previous.get(signum)
        if callable(previous):
            # Nhường lại cho server để quá trình shutdown thật sự tiếp tục.
            previous(signum, frame)

    def install(self) -> None:
        """Đăng ký handler cho SIGTERM và SIGINT, nhớ lại handler cũ.

        TODO (CP4): với mỗi tín hiệu trong ``(signal.SIGTERM, signal.SIGINT)``:

            self._previous[sig] = signal.getsignal(sig)   # nhớ handler cũ
            signal.signal(sig, self.request_shutdown)     # rồi mới ghi đè

        SIGTERM: orchestrator yêu cầu tắt. SIGINT: bạn bấm Ctrl+C.
        """
        # Lưu handler hiện tại trước khi đăng ký handler mới.
        for sig in (signal.SIGTERM, signal.SIGINT):
            # Nhớ handler của Uvicorn hoặc handler trước đó.
            self._previous[sig] = signal.getsignal(sig)
            # Đăng ký bound method; Python sẽ gọi method với signal/frame.
            signal.signal(sig, self.request_shutdown)


# Một instance dùng chung cho cả app
lifecycle = Lifecycle()
