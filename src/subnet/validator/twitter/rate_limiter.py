from collections import deque
import time

from loguru import logger


class RateLimiter:
    def __init__(self, max_calls, period):
        """
        :param max_calls: Maximum number of allowed calls within the period.
        :param period: The time window (in seconds) for rate limiting.
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            current_time = time.time()

            # Remove timestamps older than the allowed period
            while self.calls and current_time - self.calls[0] > self.period:
                self.calls.popleft()

            # If we have reached the rate limit, calculate wait time
            if len(self.calls) >= self.max_calls:
                wait_time = self.period - (current_time - self.calls[0])
                logger.warning(f"Rate limit reached. Waiting for {int(wait_time)} seconds...", wait_time=wait_time)
                time.sleep(wait_time)

            # Record the time of this request and proceed with the function call
            self.calls.append(time.time())
            return func(*args, **kwargs)

        return wrapper
