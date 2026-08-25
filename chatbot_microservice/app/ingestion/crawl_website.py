from collections import deque
from hashlib import md5
from html import unescape
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js",
    ".ico", ".zip", ".mp4", ".pdf",
)

MIN_WORDS = 80
REQUEST_TIMEOUT_SECONDS = 12


def _fetch_with_requests(url: str) -> str:
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower():
            return ""
        return response.text
    except Exception as exc:
        print(f"Requests fallback failed for {url}: {exc}")
        return ""


def fetch_page(url: str, timeout: int = 20000) -> str:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                )

                page.goto(
                    url,
                    timeout=timeout,
                    wait_until="domcontentloaded",
                )

                # Some sites never reach networkidle because of analytics/live scripts.
                # Treat this as best-effort, then still collect rendered HTML.
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass

                page.wait_for_timeout(1000)
                return page.content()
            finally:
                browser.close()

    except Exception as exc:
        print(f"Playwright fetch failed for {url}: {exc}")
        return _fetch_with_requests(url)


def _same_site(url: str, base_netloc: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    netloc = parsed.netloc.lower().replace("www.", "")
    base = base_netloc.lower().replace("www.", "")
    return netloc == base


def _normalize_url(url: str) -> str:
    url = urldefrag(url)[0]
    if "?" in url:
        url = url.split("?")[0]
    return url.rstrip("/")


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup([
        "script", "style", "noscript", "svg", "footer", "nav", "aside",
        "header", "form",
    ]):
        tag.decompose()

    main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup
    text = main_content.get_text("\n")

    lines = [unescape(line.strip()) for line in text.splitlines()]
    cleaned_lines = []

    for line in lines:
        if not line or len(line) < 3:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def crawl_site(
    start_url: str,
    max_pages: int = 80,
    timeout: int = 20000,
) -> list[dict[str, str]]:
    parsed_start = urlparse(start_url)
    base_netloc = parsed_start.netloc
    queue = deque([start_url])
    visited: set[str] = set()
    seen_hashes: set[str] = set()
    pages: list[dict[str, str]] = []

    while queue and len(pages) < max_pages:
        url = _normalize_url(queue.popleft())

        if url in visited or url.lower().endswith(SKIP_EXTENSIONS):
            continue

        visited.add(url)
        print(f"Crawling: {url}")

        html = fetch_page(url, timeout=timeout)
        if not html:
            continue

        text = _clean_text(html)
        if len(text.split()) < MIN_WORDS:
            print(f"Skipped low-content page: {url}")
            continue

        content_hash = md5(text.encode("utf-8")).hexdigest()
        if content_hash in seen_hashes:
            continue

        seen_hashes.add(content_hash)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url

        print(f"Collected page: {url}")
        pages.append({"url": url, "title": title, "text": text})

        for link in soup.find_all("a", href=True):
            next_url = _normalize_url(urljoin(url, link["href"]))
            if _same_site(next_url, base_netloc) and next_url not in visited:
                queue.append(next_url)

    return pages
