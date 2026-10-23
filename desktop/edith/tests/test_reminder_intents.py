"""Unit tests for Natural Language Reminder, Timer, Agenda, and Mode Reflexes."""

from edith.core.config import CONFIG
from edith.tools.reflex import REFLEX


def test_reflex_remind_me_at_time():
    """Verify natural language reminder matching and execution."""
    m = REFLEX.evaluate("remind me to wash clothes at 7:30 pm")
    assert m is not None
    assert m.command_name == "set_reminder"

    res = REFLEX.execute_match(m)
    assert "Reminder set" in res
    assert "wash clothes" in res


def test_reflex_remind_me_every_weekday():
    """Verify recurring weekday reminder."""
    m = REFLEX.evaluate("remind me to join standup every weekday at 10 am")
    assert m is not None
    assert m.command_name == "set_reminder"

    res = REFLEX.execute_match(m)
    assert "Reminder set" in res
    assert "weekdays" in res


def test_reflex_remind_me_arrival():
    """Verify arrival-triggered reminder."""
    m = REFLEX.evaluate("remind me to turn on geyser when I reach home")
    assert m is not None
    assert m.command_name == "set_reminder"

    res = REFLEX.execute_match(m)
    assert "Reminder set" in res
    assert "Arrived" in res


def test_reflex_timer():
    """Verify countdown timer reflex."""
    m = REFLEX.evaluate("timer 10 minutes")
    assert m is not None
    assert m.command_name == "set_timer"

    res = REFLEX.execute_match(m)
    assert "Timer started" in res
    assert "10 minute" in res


def test_reflex_today_agenda():
    """Verify today's agenda query reflex."""
    m = REFLEX.evaluate("what's on today")
    assert m is not None
    assert m.command_name == "today_agenda"

    res = REFLEX.execute_match(m)
    assert "Schedule for Today" in res


def test_reflex_upcoming_holidays():
    """Verify upcoming holidays query reflex."""
    m = REFLEX.evaluate("what are the next upcoming holidays")
    assert m is not None
    assert m.command_name == "upcoming_holidays"

    res = REFLEX.execute_match(m)
    assert "Upcoming Indian Holidays" in res


def test_reflex_mode_switches():
    """Verify offline, online, and auto mode switching reflexes."""
    m1 = REFLEX.evaluate("go offline")
    assert m1 is not None
    assert m1.command_name == "set_mode_offline"
    res1 = REFLEX.execute_match(m1)
    assert "OFFLINE" in res1
    assert CONFIG.offline_mode is True

    m2 = REFLEX.evaluate("go online")
    assert m2 is not None
    assert m2.command_name == "set_mode_online"
    res2 = REFLEX.execute_match(m2)
    assert "ONLINE" in res2
    assert CONFIG.offline_mode is False

    m3 = REFLEX.evaluate("auto mode")
    assert m3 is not None
    assert m3.command_name == "set_mode_auto"
    res3 = REFLEX.execute_match(m3)
    assert "AUTO" in res3
    assert CONFIG.manual_mode == "auto"
