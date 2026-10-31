"""Unit tests for the breaker's state machine. A fake clock replaces real waiting."""
import asyncio

import pytest

from breaker import CLOSED, HALF_OPEN, OPEN, CircuitBreaker, CircuitOpenError


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class RemoteDown(Exception):
    pass


async def ok():
    return "ok"


async def fail():
    raise RemoteDown()


async def not_found():
    raise KeyError("unknown book")  # not in failure_exceptions


def make_breaker(clock):
    return CircuitBreaker("test", failure_threshold=3, open_seconds=10,
                          failure_exceptions=(RemoteDown,), clock=clock)


def run(coro):
    return asyncio.run(coro)


def trip(breaker):
    for _ in range(3):
        with pytest.raises(RemoteDown):
            run(breaker.call(fail))


def test_opens_after_threshold_consecutive_failures():
    breaker = make_breaker(FakeClock())
    for _ in range(2):
        with pytest.raises(RemoteDown):
            run(breaker.call(fail))
    assert breaker.state == CLOSED
    with pytest.raises(RemoteDown):
        run(breaker.call(fail))
    assert breaker.state == OPEN


def test_success_resets_the_failure_count():
    breaker = make_breaker(FakeClock())
    for _ in range(2):
        with pytest.raises(RemoteDown):
            run(breaker.call(fail))
    run(breaker.call(ok))
    with pytest.raises(RemoteDown):
        run(breaker.call(fail))
    assert breaker.state == CLOSED
    assert breaker.failures == 1


def test_open_breaker_rejects_without_calling_the_remote():
    clock = FakeClock()
    breaker = make_breaker(clock)
    trip(breaker)
    calls = []

    async def remote():
        calls.append(1)
        return "ok"

    clock.now += 4
    with pytest.raises(CircuitOpenError) as error:
        run(breaker.call(remote))
    assert calls == []
    assert error.value.retry_after == pytest.approx(6)


def test_half_open_success_closes_the_breaker():
    clock = FakeClock()
    breaker = make_breaker(clock)
    trip(breaker)
    clock.now += 10
    assert run(breaker.call(ok)) == "ok"
    assert breaker.state == CLOSED
    assert breaker.failures == 0


def test_half_open_failure_opens_it_again_for_a_full_period():
    clock = FakeClock()
    breaker = make_breaker(clock)    # threshold 3, open for 10 s
    trip(breaker)                    # 3 failures in a row
    clock.now += 10
    with pytest.raises(RemoteDown):
        run(breaker.call(fail))
    assert breaker.state == OPEN
    assert breaker.retry_after() == pytest.approx(10)


def test_half_open_lets_only_one_trial_call_through():
    clock = FakeClock()
    breaker = make_breaker(clock)
    trip(breaker)
    clock.now += 10

    async def two_calls_at_once():
        release = asyncio.Event()

        async def slow_trial():
            await release.wait()
            return "ok"

        trial = asyncio.create_task(breaker.call(slow_trial))
        await asyncio.sleep(0)  # the trial call is now in flight
        assert breaker.state == HALF_OPEN
        with pytest.raises(CircuitOpenError):
            await breaker.call(ok)
        release.set()
        return await trial

    assert run(two_calls_at_once()) == "ok"
    assert breaker.state == CLOSED


def test_errors_that_are_not_remote_failures_do_not_count():
    breaker = make_breaker(FakeClock())
    for _ in range(5):
        with pytest.raises(KeyError):
            run(breaker.call(not_found))
    assert breaker.state == CLOSED
    assert breaker.failures == 0
