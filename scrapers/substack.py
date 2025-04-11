"""
Substack scraper for Writer Context Protocol.
"""
import logging
from datetime import datetime
from typing import List
import re

import feedparser
import httpx
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Post

logger = logging.getLogger(__name__)


class SubstackScraper(BaseScraper):
    """Scraper for Substack blogs."""
    
    async def scrape(self) -> List[Post]:
        """
        Scrape posts from a Substack blog.
        
        Returns:
            A list of Post objects with content and metadata
        """
        try:
            logger.info(f"Fetching Substack posts from: {self.url}")
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{self.url}feed")
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                logger.info(f"Number of entries in feed: {len(feed.entries)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Substack feed: {str(e)}")
            return []

        posts = []
        for entry in feed.entries[:self.max_posts]:
            try:
                content = entry.content[0].value if 'content' in entry else entry.summary
                soup = BeautifulSoup(content, 'html.parser')
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
                    subtitle="",
                )
                posts.append(post)
            except Exception as e:
                logger.error(f"Error processing Substack post {entry.get('link', 'unknown')}: {str(e)}")

        logger.info(f"Scraped {len(posts)} posts from Substack")
        return posts
        
    @staticmethod
    def _clean_content(content: str) -> str:
        """Remove extra whitespace and normalize text."""
        # Remove extra whitespace and newlines
        content = re.sub(r'\s+', ' ', content).strip()
        return content 