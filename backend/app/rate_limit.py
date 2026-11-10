import time
from collections import OrderedDict, deque
from threading import Lock

from flask import abort, request


def install_rate_limits(app):
    buckets, lock = OrderedDict(), Lock()

    @app.before_request
    def rate_limit():
        if app.config.get("TESTING") and not app.config.get("TEST_RATE_LIMIT"):
            return
        if request.method not in {"POST", "PUT", "DELETE", "PATCH"}:
            return
        limit = (
            12
            if request.path in {"/auth", "/reg", "/recover", "/verification", "/resend_code"}
            else 40
        )
        key = (request.remote_addr, "auth" if limit == 12 else "write")
        current = time.monotonic()
        with lock:
            if key not in buckets:
                if len(buckets) >= 4096:
                    buckets.popitem(last=False)
                buckets[key] = deque()
            bucket = buckets[key]
            while bucket and bucket[0] < current - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                abort(429, description="Слишком много запросов. Подождите минуту.")
            bucket.append(current)
            buckets.move_to_end(key)
