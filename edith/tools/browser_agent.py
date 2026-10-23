"""Headless Browser and Web Intelligence Agent for EDITH.

Implements Sections 22, 53, and 61 of the Master Engineering Constitution.
Provides autonomous web browsing, document parsing, link extraction,
and headless screenshots via Windows native Microsoft Edge or Chrome.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edith.tools.browser_agent")


@dataclass
class PageContent:
    """Parsed structured web content."""
    url: str
    title: str
    text_content: str
    links: List[Dict[str, str]] = field(default_factory=list)
    status_code: int = 200
    load_time_ms: float = 0.0


class HeadlessBrowserAgent:
    """Autonomous web exploration and scraping engine."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or "d:/EDITH final boss/edith/data/screenshots")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 EDITH/6.1"

    def fetch_page(self, url: str, max_chars: int = 8000) -> PageContent:
        """Fetch and parse clean text and hyperlinks from a URL."""
        t0 = time.perf_counter()
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        req = urllib.request.Request(
            clean_url,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
        )

        try:
            with urllib.request.urlopen(req, timeout=12.0) as res:
                status = res.status
                raw_html = res.read().decode("utf-8", errors="replace")
        except Exception as ex:
            dt = (time.perf_counter() - t0) * 1000.0
            logger.warning("Browser fetch failed for %s: %s", clean_url, ex)
            return PageContent(
                url=clean_url,
                title="Error Loading Page",
                text_content=f"Error fetching URL: {ex}",
                status_code=500,
                load_time_ms=dt,
            )

        dt = (time.perf_counter() - t0) * 1000.0
        title_m = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_m.group(1).strip()) if title_m else "No Title"

        # Strip scripts, styles, and svg
        no_scripts = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)

        # Extract links
        links = []
        for m in re.finditer(r'<a\s+[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>', no_scripts, re.IGNORECASE | re.DOTALL):
            href = m.group(1).strip()
            text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if href and not href.startswith(("#", "javascript:")):
                abs_href = urllib.parse.urljoin(clean_url, href)
                links.append({"text": text or abs_href, "url": abs_href})

        # Strip tags and normalize whitespace
        raw_text = re.sub(r"<[^>]+>", " ", no_scripts)
        clean_text = re.sub(r"\s+", " ", html.unescape(raw_text)).strip()
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + "\n... [Content truncated]"

        return PageContent(
            url=clean_url,
            title=title,
            text_content=clean_text,
            links=links[:30],
            status_code=status,
            load_time_ms=dt,
        )

    def capture_screenshot(self, url: str, output_name: Optional[str] = None) -> Optional[str]:
        """Capture full-page screenshot using headless Windows Edge or Chrome."""
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        target_file = self.cache_dir / (output_name or f"web_snap_{int(time.time())}.png")

        # Find Edge or Chrome executable
        browser_exe = None
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            shutil.which("msedge"),
            shutil.which("chrome"),
        ]
        for c in candidates:
            if c and os.path.exists(c):
                browser_exe = c
                break

        if not browser_exe:
            logger.warning("No native browser found for headless screenshot.")
            return None

        cmd = [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            f"--screenshot={str(target_file)}",
            "--window-size=1280,800",
            clean_url,
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, timeout=15.0)
            if target_file.exists() and target_file.stat().st_size > 0:
                logger.info("Captured headless screenshot: %s", target_file)
                return str(target_file)
        except Exception as ex:
            logger.warning("Headless screenshot error: %s", ex)

        return None


# Global Singleton Instance
BROWSER_AGENT = HeadlessBrowserAgent()
