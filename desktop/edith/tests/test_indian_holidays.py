"""Unit tests for Indian National and Gazetted Holiday System."""

from edith.data.holidays import (
    HOLIDAY_SOURCE,
    NATIONAL_HOLIDAYS,
    GAZETTED_HOLIDAYS,
    has_gazetted_data,
    get_holidays_between,
    get_upcoming_holidays,
)


def test_national_holidays_presence():
    """Verify standard 3 national holidays are defined."""
    assert len(NATIONAL_HOLIDAYS) == 3
    names = [h["name"] for h in NATIONAL_HOLIDAYS]
    assert "Republic Day" in names
    assert "Independence Day" in names
    assert "Mahatma Gandhi Jayanti" in names


def test_gazetted_holidays_2026():
    """Verify gazetted holidays for Central Govt offices (DoPT 2026)."""
    assert has_gazetted_data(2026) is True
    assert has_gazetted_data(2010) is False

    g2026 = GAZETTED_HOLIDAYS[2026]
    assert len(g2026) >= 14
    names = [h["name"] for h in g2026]
    assert "Holi" in names
    assert "Good Friday" in names
    assert "Diwali (Deepavali)" in names
    assert "Christmas Day" in names

    # Verify moon-sighting tentative flags
    id_ul_fitr = next(h for h in g2026 if "Id-ul-Fitr" in h["name"])
    assert id_ul_fitr["tentative"] is True


def test_get_holidays_between_range():
    """Verify date range filtering and expansion."""
    hols = get_holidays_between("2026-01-01", "2026-03-31")
    names = [h["name"] for h in hols]
    assert "Republic Day" in names  # 2026-01-26 (national)
    assert "Holi" in names          # 2026-03-04 (gazetted)
    assert all(h["source"] for h in hols)


def test_category_filtering():
    """Verify filtering by national or gazetted categories."""
    nat_only = get_holidays_between("2026-01-01", "2026-12-31", categories=["national"])
    assert all(h["category"] == "national" for h in nat_only)
    assert len(nat_only) == 3

    gaz_only = get_holidays_between("2026-01-01", "2026-12-31", categories=["gazetted"])
    assert all(h["category"] == "gazetted" for h in gaz_only)
    assert len(gaz_only) >= 14


def test_get_upcoming_holidays():
    """Verify upcoming holidays returns formatted list."""
    upcoming = get_upcoming_holidays(limit=3)
    assert len(upcoming) <= 3
    if upcoming:
        assert "date" in upcoming[0]
        assert "name" in upcoming[0]
