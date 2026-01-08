"""
Web content fetcher for static pages.

Uses requests + BeautifulSoup for HTML fetching and parsing,
and html2text for Markdown conversion.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import html2text
import requests
from bs4 import BeautifulSoup, Tag


@dataclass
class FetchResult:
    """Result of fetching a web page."""

    url: str
    title: str
    content: str  # Markdown format
    success: bool
    error: Optional[str] = None


class WebFetcher:
    """
    Fetches and extracts article content from static web pages.

    Features:
    - Smart content extraction (article, main, content areas)
    - Markdown conversion
    - Title extraction
    - Error handling with detailed messages
    """

    # Common user agent to avoid basic blocking
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 30

    # Content selectors in priority order
    CONTENT_SELECTORS = [
        "article",
        '[role="main"]',
        "main",
        ".post-content",
        ".article-content",
        ".entry-content",
        ".content",
        "#content",
        ".post",
        ".article",
        "#article",
        ".markdown-body",  # GitHub
        ".prose",  # Tailwind prose
    ]

    # Elements to remove from content
    REMOVE_SELECTORS = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        ".sidebar",
        ".navigation",
        ".nav",
        ".menu",
        ".ads",
        ".advertisement",
        ".social-share",
        ".comments",
        ".related-posts",
        ".newsletter",
        '[role="navigation"]',
        '[role="banner"]',
        '[role="complementary"]',
    ]

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the web fetcher.

        Args:
            user_agent: Custom user agent string.
            timeout: Request timeout in seconds.
        """
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout

        # Configure html2text
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # Don't wrap lines
        self.html_converter.unicode_snob = True
        self.html_converter.skip_internal_links = True

    def fetch(self, url: str) -> FetchResult:
        """
        Fetch and extract content from a URL.

        Args:
            url: The URL to fetch.

        Returns:
            FetchResult with extracted content or error information.
        """
        # Validate URL
        if not self._is_valid_url(url):
            return FetchResult(
                url=url,
                title="",
                content="",
                success=False,
                error=f"Invalid URL: {url}",
            )

        try:
            # Fetch HTML
            html_content = self._fetch_html(url)

            # Parse and extract content
            title, content = self._extract_content(html_content, url)

            if not content.strip():
                return FetchResult(
                    url=url,
                    title=title,
                    content="",
                    success=False,
                    error="Could not extract article content from the page",
                )

            return FetchResult(
                url=url,
                title=title,
                content=content,
                success=True,
            )

        except requests.exceptions.Timeout:
            return FetchResult(
                url=url,
                title="",
                content="",
                success=False,
                error=f"Request timed out after {self.timeout} seconds",
            )
        except requests.exceptions.ConnectionError as e:
            return FetchResult(
                url=url,
                title="",
                content="",
                success=False,
                error=f"Connection error: {str(e)}",
            )
        except requests.exceptions.RequestException as e:
            return FetchResult(
                url=url,
                title="",
                content="",
                success=False,
                error=f"Request failed: {str(e)}",
            )
        except Exception as e:
            return FetchResult(
                url=url,
                title="",
                content="",
                success=False,
                error=f"Unexpected error: {str(e)}",
            )

    def _is_valid_url(self, url: str) -> bool:
        """Check if the URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from URL."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=self.timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Try to detect encoding
        response.encoding = response.apparent_encoding or "utf-8"

        return response.text

    def _extract_content(self, html: str, base_url: str) -> Tuple[str, str]:
        """
        Extract title and main content from HTML.

        Args:
            html: Raw HTML content.
            base_url: Base URL for resolving relative links.

        Returns:
            Tuple of (title, markdown_content).
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title(soup)

        # Remove unwanted elements
        self._remove_unwanted_elements(soup)

        # Find main content
        content_element = self._find_content_element(soup)

        if content_element is None:
            # Fallback to body if no content element found
            content_element = soup.body

        if content_element is None:
            return title, ""

        # Fix relative URLs
        self._fix_relative_urls(content_element, base_url)

        # Convert to Markdown
        markdown = self.html_converter.handle(str(content_element))

        # Clean up markdown
        markdown = self._clean_markdown(markdown)

        return title, markdown

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try h1 in article
        article = soup.find("article")
        if article:
            h1 = article.find("h1")
            if h1:
                return h1.get_text().strip()

        # Try first h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        # Fall back to title tag
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
            # Remove common suffixes
            for separator in [" - ", " | ", " – ", " — ", " :: "]:
                if separator in title:
                    title = title.split(separator)[0].strip()
            return title

        return "Untitled"

    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from the soup."""
        for selector in self.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

    def _find_content_element(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the main content element."""
        for selector in self.CONTENT_SELECTORS:
            element = soup.select_one(selector)
            if element and self._has_substantial_content(element):
                return element
        return None

    def _has_substantial_content(self, element: Tag) -> bool:
        """Check if an element has substantial text content."""
        text = element.get_text(strip=True)
        # At least 100 characters of text content
        return len(text) > 100

    def _fix_relative_urls(self, element: Tag, base_url: str) -> None:
        """Convert relative URLs to absolute URLs."""
        # Fix links
        for link in element.find_all("a", href=True):
            href = link["href"]
            if not href.startswith(("http://", "https://", "mailto:", "#")):
                link["href"] = urljoin(base_url, href)

        # Fix images
        for img in element.find_all("img", src=True):
            src = img["src"]
            if not src.startswith(("http://", "https://", "data:")):
                img["src"] = urljoin(base_url, src)

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up the converted Markdown."""
        # Remove excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Remove leading/trailing whitespace
        markdown = markdown.strip()

        # Remove common noise patterns
        noise_patterns = [
            r"^\s*Share\s*$",
            r"^\s*Tweet\s*$",
            r"^\s*Pin\s*$",
            r"^\s*Email\s*$",
            r"^\s*Print\s*$",
            r"^\s*\d+ (comment|view|share|like)s?\s*$",
        ]
        for pattern in noise_patterns:
            markdown = re.sub(pattern, "", markdown, flags=re.MULTILINE | re.IGNORECASE)

        # Clean up again after removing noise
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        return markdown.strip()


# Convenience function for direct usage
def fetch_article(url: str) -> FetchResult:
    """
    Fetch and extract article content from a URL.

    Args:
        url: The URL to fetch.

    Returns:
        FetchResult with extracted content or error information.
    """
    fetcher = WebFetcher()
    return fetcher.fetch(url)
