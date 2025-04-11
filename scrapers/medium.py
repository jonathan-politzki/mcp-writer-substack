"""
Medium scraper for Writer Context Protocol.
"""
import logging
from datetime import datetime
from typing import List
import re
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Post

logger = logging.getLogger(__name__)


class MediumScraper(BaseScraper):
    """Scraper for Medium blogs."""
    
    async def scrape(self) -> List[Post]:
        """
        Scrape posts from a Medium blog.
        
        Returns:
            A list of Post objects with content and metadata
        """
        # Extract username from URL
        parsed_url = urlparse(self.url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if parsed_url.netloc == 'medium.com':
            username = path_parts[0] if path_parts else ''
        else:
            username = parsed_url.netloc.split('.')[0]
        
        if username.startswith('@'):
            username = username[1:]
        
        # Construct RSS URL
        rss_url = f'https://medium.com/feed/@{username}'
        
        try:
            logger.info(f"Fetching RSS feed from: {rss_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(rss_url)
                response.raise_for_status()
                logger.info(f"RSS feed fetched successfully. Status code: {response.status_code}")
                feed = feedparser.parse(response.text)
                logger.info(f"Number of entries in feed: {len(feed.entries)}")
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {str(e)}")
            return []

        posts = []
        for entry in feed.entries[:self.max_posts]:
            try:
                soup = BeautifulSoup(entry.content[0].value, 'html.parser')
                cleaned_text = self._clean_content(soup.get_text(separator=' ', strip=True))
                
                # Parse date
                pub_date = None
                if hasattr(entry, 'published'):
                    try:
                        # RFC 2822 format used by RSS
                        pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
                    except ValueError:
                        # Try without timezone
                        try:
                            pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S")
                        except ValueError:
                            logger.warning(f"Could not parse date: {entry.published}")
                
                post = Post(
                    title=self._clean_content(entry.title),
                    url=entry.link,
                    content=cleaned_text,
                    date=pub_date,
                    subtitle='',
                )
                posts.append(post)
            except Exception as e:
                logger.error(f"Error processing Medium post {entry.get('link', 'unknown')}: {str(e)}")

        logger.info(f"Scraped {len(posts)} posts from Medium")
        return posts
        
    @staticmethod
    def _clean_content(content: str) -> str:
        """Remove extra whitespace and normalize text."""
        # Remove extra whitespace and newlines
        content = re.sub(r'\s+', ' ', content).strip()
        return content 