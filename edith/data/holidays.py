"""Indian National and Gazetted Holiday System for EDITH.

Source: Government of India, DoPT O.M. F.No.12/2/2023-JCA dated 03-07-2025
(holidays for Central Government offices, Delhi/New Delhi, 2026).
Dates marked tentative depend on moon sighting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

HOLIDAY_SOURCE = "DoPT O.M. F.No.12/2/2023-JCA (03 Jul 2025), Central Govt offices, Delhi"
HOLIDAY_DATA_UPDATED = "2026-01 (verified against published DoPT list)"

NATIONAL_HOLIDAYS: List[Dict[str, str]] = [
    {"md": "01-26", "name": "Republic Day"},
    {"md": "08-15", "name": "Independence Day"},
    {"md": "10-02", "name": "Mahatma Gandhi Jayanti"},
]

GAZETTED_HOLIDAYS: Dict[int, List[Dict[str, Any]]] = {
    2026: [
        {"date": "2026-03-04", "name": "Holi", "tentative": False},
        {"date": "2026-03-21", "name": "Id-ul-Fitr", "tentative": True},
        {"date": "2026-03-26", "name": "Ram Navami", "tentative": False},
        {"date": "2026-03-31", "name": "Mahavir Jayanti", "tentative": False},
        {"date": "2026-04-03", "name": "Good Friday", "tentative": False},
        {"date": "2026-05-01", "name": "Buddha Purnima", "tentative": False},
        {"date": "2026-05-27", "name": "Id-ul-Zuha (Bakrid)", "tentative": True},
        {"date": "2026-06-26", "name": "Muharram", "tentative": True},
        {"date": "2026-08-26", "name": "Milad-un-Nabi (Id-e-Milad)", "tentative": True},
        {"date": "2026-09-04", "name": "Janmashtami (Vaishnava)", "tentative": False},
        {"date": "2026-10-20", "name": "Dussehra (Vijaya Dashami)", "tentative": False},
        {"date": "2026-11-08", "name": "Diwali (Deepavali)", "tentative": False},
        {"date": "2026-11-24", "name": "Guru Nanak Jayanti", "tentative": False},
        {"date": "2026-12-25", "name": "Christmas Day", "tentative": False},
    ]
}


def has_gazetted_data(year: int) -> bool:
    """Check if gazetted holiday calendar is verified for given year."""
    return year in GAZETTED_HOLIDAYS


def get_holidays_between(
    from_date: str,
    to_date: str,
    categories: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return holidays between from_date and to_date (YYYY-MM-DD inclusive)."""
    if categories is None:
        categories = ["national", "gazetted"]

    out: List[Dict[str, Any]] = []
    y0 = int(from_date[:4])
    y1 = int(to_date[:4])

    for y in range(y0, y1 + 1):
        if "national" in categories:
            for n in NATIONAL_HOLIDAYS:
                d = f"{y}-{n['md']}"
                if from_date <= d <= to_date:
                    out.append({
                        "date": d,
                        "name": n["name"],
                        "category": "national",
                        "tentative": False,
                        "source": "Constitution/national holiday (fixed date)",
                    })

        if "gazetted" in categories and y in GAZETTED_HOLIDAYS:
            for g in GAZETTED_HOLIDAYS[y]:
                d = g["date"]
                if from_date <= d <= to_date:
                    out.append({
                        "date": d,
                        "name": g["name"],
                        "category": "gazetted",
                        "tentative": bool(g.get("tentative", False)),
                        "source": HOLIDAY_SOURCE,
                    })

    out.sort(key=lambda x: x["date"])
    return out


def get_upcoming_holidays(limit: int = 5) -> List[Dict[str, Any]]:
    """Get the next upcoming Indian holidays from today."""
    from datetime import date
    today = date.today().isoformat()
    end = f"{date.today().year + 1}-12-31"
    holidays = get_holidays_between(today, end)
    return holidays[:limit]
