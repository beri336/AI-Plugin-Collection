# tests/test_decorators.py

'''
Unit tests for decorators
  This test suite validates all reusable function decorators.

- Tests exception handling with configurable fallback
- Validates model name validation in function parameters
- Checks retry logic with exponential backoff
- Tests result caching with TTL expiration
- Validates execution logging for success and failure scenarios
- Checks service running requirements before function execution
- Tests performance timing decorator
- Uses mocks for isolated decorator tests
'''

from unittest.mock import patch, MagicMock
from core import decorators
import pytest
import time

# --------------------------------------------------------------------
# handle_exceptions
# --------------------------------------------------------------------
def test_handle_exceptions_returns_default(caplog):
    @decorators.handle_exceptions(default_return="fallback")
    def boom(): raise ValueError("explode")

    result = boom()
    assert result == "fallback"
    assert any("Error in boom" in msg for msg in caplog.text.splitlines())


def test_handle_exceptions_raise_on_error():
    @decorators.handle_exceptions(raise_on_error=True)
    def boom(): raise RuntimeError("fail!")

    with pytest.raises(RuntimeError):
        boom()

# --------------------------------------------------------------------
# validate_model_name
# --------------------------------------------------------------------
def test_validate_model_name_valid():
    @decorators.validate_model_name
    def dummy(self, model: str): return model.upper()

    assert dummy(None, "llama") == "LLAMA"


def test_validate_model_name_invalid():
    @decorators.validate_model_name
    def dummy(self, model: str): return "OK"

    with pytest.raises(ValueError):
        dummy(None, "")

# --------------------------------------------------------------------
# retry_on_failure
# --------------------------------------------------------------------
@patch("time.sleep", return_value=None)
def test_retry_on_failure_succeeds_after_retry(mock_sleep):
    call_counter = {"n": 0}

    class Dummy:
        @decorators.retry_on_failure(max_attempts=3, delay=0.1, backoff=0.1)
        def flaky(self):
            call_counter["n"] += 1
            if call_counter["n"] < 3:
                raise ConnectionError("temp fail")
            return "ok"

    d = Dummy()
    result = d.flaky()
    assert result == "ok"
    assert call_counter["n"] == 3
    assert mock_sleep.call_count == 2

@patch("time.sleep", return_value=None)
def test_retry_on_failure_exhausts_retries(mock_sleep):
    class Dummy:
        @decorators.retry_on_failure(max_attempts=2, delay=0.1)
        def always_fail(self): raise TimeoutError("dead")

    d = Dummy()
    with pytest.raises(TimeoutError):
        d.always_fail()
    assert mock_sleep.called

# --------------------------------------------------------------------
# cache_result
# --------------------------------------------------------------------
def test_cache_result_basic():
    calls = {"n": 0}

    @decorators.cache_result(ttl_seconds=1)
    def compute(x): 
        calls["n"] += 1
        return x * 2

    # first call triggers calculation
    assert compute(3) == 6
    # second call uses cache
    assert compute(3) == 6
    assert calls["n"] == 1

    # wait to expire cache
    time.sleep(1.1)
    assert compute(3) == 6
    assert calls["n"] == 2

# --------------------------------------------------------------------
# log_execution
# --------------------------------------------------------------------
def test_log_execution_success(caplog):
    logs = []

    class Logger:
        def debug(self, msg): logs.append(msg)
        def error(self, msg): logs.append(msg)

    class Dummy:
        @decorators.log_execution(logger=Logger())
        def foo(self):    # 👈 Methode mit `self`
            return 42

    d = Dummy()
    assert d.foo() == 42
    assert any("completed" in m for m in logs)

def test_log_execution_failure(caplog):
    logs = []

    class Logger:
        def debug(self, msg): logs.append(msg)
        def error(self, msg): logs.append(msg)

    class Dummy:
        @decorators.log_execution(logger=Logger())
        def boom(self):   # 👈 Methode mit `self`
            raise ValueError("crash")

    d = Dummy()
    with pytest.raises(ValueError):
        d.boom()
    assert any("failed" in m for m in logs)

# --------------------------------------------------------------------
# require_running
# --------------------------------------------------------------------
@patch("modules.service_manager.Service")
def test_require_running_calls_function(mock_service):
    svc = mock_service.return_value
    svc.is_running = True

    class Dummy:
        @decorators.require_running
        def do(self): return "ok"

    d = Dummy()
    assert d.do() == "ok"


@patch("modules.service_manager.Service")
def test_require_running_raises_if_not_running(mock_service):
    svc = mock_service.return_value
    svc.is_running = False

    class Dummy:
        @decorators.require_running
        def do(self): return "ok"

    d = Dummy()
    with pytest.raises(RuntimeError, match="not running"):
        d.do()

# --------------------------------------------------------------------
# timing decorator
# --------------------------------------------------------------------
def test_timing_prints(capsys):
    @decorators.timing
    def foo(): time.sleep(0.05); return "done"

    assert foo() == "done"
    out = capsys.readouterr().out
    assert "foo took" in out
