"""Unit tests for System Optimizer."""

from edith.tools.system_optimizer import clean_temp_files, optimize_system, trim_process_memory


def test_trim_process_memory():
    res = trim_process_memory()
    assert isinstance(res, dict)
    assert res["success"] is True


def test_clean_temp_files():
    res = clean_temp_files(max_files=10)
    assert isinstance(res, dict)
    assert "cleaned_count" in res
    assert "mb_freed" in res


def test_optimize_system():
    res = optimize_system()
    assert isinstance(res, str)
    assert "Optimization complete" in res
