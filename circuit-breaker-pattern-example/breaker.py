"""A small circuit breaker with three states: CLOSED, OPEN and HALF_OPEN.

CLOSED:    calls go through. Consecutive failures are counted; a success resets the count.
OPEN:      calls fail at once with CircuitOpenError, without touching the remote service.
HALF_OPEN: after open_seconds, one trial call is let through. Success closes the
           breaker, failure opens it again for another open_seconds.
"""
import time

CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"


class CircuitOpenError(Exception):
    """Raised instead of calling the remote service while the breaker is open."""

    def __init__(self, name, retry_after):
        super().__init__(f"circuit '{name}' is open, retry after {retry_after:.1f} s")
        self.retry_after = retry_after


class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, open_seconds=10.0,
                 failure_exceptions=(Exception,), clock=time.monotonic):
        self.name = name
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.failure_exceptions = failure_exceptions
        self.clock = clock
        self.state = CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self.trial_running = False

    def _move_to(self, new_state, reason):
        print(f"breaker {self.name}: {self.state} -> {new_state} ({reason})", flush=True)
        self.state = new_state

    def retry_after(self):
        return max(0.0, self.opened_at + self.open_seconds - self.clock())

    def _before_call(self):
        if self.state == OPEN:
            if self.retry_after() > 0:
                raise CircuitOpenError(self.name, self.retry_after())
            self._move_to(HALF_OPEN, f"{self.open_seconds:g} s passed, letting one trial call through")
        if self.state == HALF_OPEN:
            if self.trial_running:
                # Only one trial call at a time; everyone else is still rejected.
                raise CircuitOpenError(self.name, self.open_seconds)
            self.trial_running = True

    def _on_success(self):
        if self.state == HALF_OPEN:
            self.trial_running = False
            self._move_to(CLOSED, "trial call succeeded")
        self.failures = 0

    def _on_failure(self, error):
        if self.state == HALF_OPEN:
            self.trial_running = False
            self.opened_at = self.clock()
            self._move_to(OPEN, f"trial call failed: {type(error).__name__}")
            return
        self.failures += 1
        if self.state == CLOSED and self.failures >= self.failure_threshold:
            self.opened_at = self.clock()
            self._move_to(OPEN, f"{self.failures} consecutive failures, last: {type(error).__name__}")

    async def call(self, func, *args, **kwargs):
        self._before_call()
        try:
            result = await func(*args, **kwargs)
        except self.failure_exceptions as error:
            self._on_failure(error)
            raise
        except BaseException:
            # Not a failure of the remote service (for example a bug in our code
            # or a cancelled request). Free the trial slot but don't count it.
            if self.state == HALF_OPEN:
                self.trial_running = False
            raise
        self._on_success()
        return result

    def snapshot(self):
        return {
            "name": self.name,
            "state": self.state,
            "consecutive_failures": self.failures,
            "retry_after_seconds": round(self.retry_after(), 1) if self.state == OPEN else None,
        }
