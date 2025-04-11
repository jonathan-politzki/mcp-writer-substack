"""
Base scraper functionality for Writer Context Protocol.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Post:
    """Representation of a blog post with content and metadata."""
    title: str
    url: str
    content: str
    date: Optional[datetime] = None
    subtitle: str = ""
    word_count: int = 0

    def __post_init__(self):
        """Calculate word count if not provided."""
        if not self.word_count and self.content:
            self.word_count = len(self.content.split())


class BaseScraper(ABC):
    """Base class for platform-specific scrapers."""
    
    def __init__(self, url: str, max_posts: int = 10):
        """
        Initialize a scraper with configuration.
        
        Args:
            url: The URL of the blog to scrape
            max_posts: Maximum number of posts to retrieve
        """
        self.url = self._normalize_url(url)
        self.max_posts = max_posts
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize a URL to ensure consistency.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL with trailing slash
        """
        if not url.endswith("/"):
            url += "/"
        return url
    
    @abstractmethod
    async def scrape(self) -> List[Post]:
        """
        Scrape posts from the configured platform.
        
        Returns:
            A list of Post objects containing content and metadata
        """
        pass 