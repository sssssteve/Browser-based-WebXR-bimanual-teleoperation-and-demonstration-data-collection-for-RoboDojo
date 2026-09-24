"""Latest-only JPEG preview encoding outside the simulator execution thread."""
import threading
import time

from recording import jpeg


class PreviewEncoder:
    def __init__(self, publish, quality=70):
        self.publish = publish
        self.quality = quality
        self.condition = threading.Condition()
        self.pending = None
        self.closed = False
        self.encode_ms = 0.
        self.bytes = 0
        self.dropped = 0
        self.thread = threading.Thread(target=self._run, name="preview-jpeg", daemon=True)
        self.thread.start()

    def submit(self, image):
        with self.condition:
            if self.pending is not None:
                self.dropped += 1
            self.pending = image
            self.condition.notify()

    def _run(self):
        while True:
            with self.condition:
                while self.pending is None and not self.closed:
                    self.condition.wait()
                if self.pending is None and self.closed:
                    return
                image, self.pending = self.pending, None
            started = time.monotonic()
            payload = jpeg(image, quality=self.quality)
            self.encode_ms = (time.monotonic() - started) * 1000
            self.bytes = len(payload)
            self.publish(payload)

    def diagnostics(self):
        with self.condition:
            return {
                "encode_ms": round(self.encode_ms, 1),
                "bytes": self.bytes,
                "pending": self.pending is not None,
                "dropped": self.dropped,
                "thread_alive": self.thread.is_alive(),
            }

    def close(self, timeout=2):
        with self.condition:
            self.closed = True
            self.pending = None
            self.condition.notify()
        self.thread.join(timeout=timeout)
