#!/usr/bin/env python3
"""
Writer Context Tool - MCP server for accessing Substack and Medium content.

This tool allows Claude to access your writing from blogging platforms.
"""
import asyncio
import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import httpx
import feedparser
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
import numpy as np
from diskcache import Cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("writer-tool")

# Initialize FastMCP server
mcp = FastMCP("writer-tool")

# Initialize the cache directory
cache_dir = Path(".cache")
os.makedirs(cache_dir, exist_ok=True)
posts_cache = Cache(str(cache_dir / "posts"))
embeddings_cache = Cache(str(cache_dir / "embeddings"))

# Initialize the embedding model
model = None  # Lazy-loaded when needed

# Define Post class for storing article data
class Post:
    def __init__(self, title, url, content, date=None, subtitle="", platform="", platform_name=""):
        self.title = title
        self.url = url
        self.content = content
        self.date = date
        self.subtitle = subtitle
        self.word_count = len(content.split()) if content else 0
        self.platform = platform
        self.platform_name = platform_name
        
        # Generate a unique ID for this post based on URL and title
        self.id = hashlib.md5(f"{url}:{title}".encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Post object to a dictionary for serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url, 
            'content': self.content,
            'date': self.date.isoformat() if self.date else None,
            'subtitle': self.subtitle,
            'word_count': self.word_count,
            'platform': self.platform,
            'platform_name': self.platform_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create a Post object from a dictionary."""
        post = cls(
            title=data['title'],
            url=data['url'],
            content=data['content'],
            subtitle=data.get('subtitle', ''),
            platform=data.get('platform', ''),
            platform_name=data.get('platform_name', '')
        )
        
        if data.get('date'):
            post.date = datetime.fromisoformat(data['date'])
        
        post.id = data.get('id', post.id)
        post.word_count = data.get('word_count', post.word_count)
        
        return post


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json file."""
    config_path = Path("config.json")
    example_path = Path("config.example.json")
    
    if not config_path.exists():
        if example_path.exists():
            logger.warning("config.json not found, copying from example...")
            with open(example_path, 'r') as f:
                example_config = json.load(f)
            with open(config_path, 'w') as f:
                json.dump(example_config, f, indent=2)
        else:
            logger.error("No config.json or config.example.json found")
            return {
                "platforms": [],
                "max_posts": 100,  # Default to higher limit
                "cache_duration_minutes": 60 * 24 * 7,  # Default to one week
                "similar_posts_count": 10  # Default to 10 if not specified
            }
    
    with open(config_path, 'r') as f:
        return json.load(f)


async def fetch_substack_posts(url: str, max_posts: int, platform_name: str) -> List[Post]:
    """Fetch posts from a Substack blog."""
    try:
        logger.info(f"Fetching Substack posts from: {url}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Ensure URL ends with slash
            if not url.endswith("/"):
                url += "/"
                
            response = await client.get(f"{url}feed")
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            logger.info(f"Found {len(feed.entries)} posts")
    except Exception as e:
        logger.error(f"Error fetching Substack feed: {str(e)}")
        return []

    posts = []
    for entry in feed.entries[:max_posts]:
        try:
            # Extract content
            content = entry.content[0].value if 'content' in entry else entry.summary
            soup = BeautifulSoup(content, 'html.parser')
            clean_content = soup.get_text(separator=' ', strip=True)
            
            # Parse date
            pub_date = None
            if hasattr(entry, 'published'):
                try:
                    pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    try:
                        pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S")
                    except ValueError:
                        logger.warning(f"Could not parse date: {entry.published}")
            
            post = Post(
                title=entry.title,
                url=entry.link,
                content=clean_content,
                date=pub_date,
                platform="substack",
                platform_name=platform_name
            )
            posts.append(post)
        except Exception as e:
            logger.error(f"Error processing Substack post: {str(e)}")

    logger.info(f"Scraped {len(posts)} posts from Substack")
    return posts


async def fetch_medium_posts(url: str, max_posts: int, platform_name: str) -> List[Post]:
    """Fetch posts from a Medium blog."""
    # Extract username from URL
    username = url.split('@')[-1].split('/')[0] if '@' in url else url.split('/')[-1]
    rss_url = f'https://medium.com/feed/@{username}'
    
    try:
        logger.info(f"Fetching Medium posts from: {rss_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            logger.info(f"Found {len(feed.entries)} posts")
    except Exception as e:
        logger.error(f"Error fetching Medium feed: {str(e)}")
        return []

    posts = []
    for entry in feed.entries[:max_posts]:
        try:
            # Extract content
            soup = BeautifulSoup(entry.content[0].value, 'html.parser')
            clean_content = soup.get_text(separator=' ', strip=True)
            
            # Parse date
            pub_date = None
            if hasattr(entry, 'published'):
                try:
                    pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    logger.warning(f"Could not parse date: {entry.published}")
            
            post = Post(
                title=entry.title,
                url=entry.link,
                content=clean_content,
                date=pub_date,
                platform="medium",
                platform_name=platform_name
            )
            posts.append(post)
        except Exception as e:
            logger.error(f"Error processing Medium post: {str(e)}")

    logger.info(f"Scraped {len(posts)} posts from Medium")
    return posts


def get_embedding_model():
    """Lazy-load the embedding model when needed."""
    global model
    if model is None:
        logger.info("Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded")
    return model


def calculate_embedding(text: str) -> np.ndarray:
    """Calculate embeddings for a piece of text."""
    model = get_embedding_model()
    # Truncate to avoid extremely long texts
    max_length = 10000
    if len(text) > max_length:
        text = text[:max_length]
    
    return model.encode(text)


def find_similar_posts(query: str, all_posts: List[Post], top_n: int = 10) -> List[Tuple[Post, float]]:
    """Find posts similar to the query using embeddings."""
    if not all_posts:
        return []
    
    # Load config to check for custom top_n value
    config = load_config()
    custom_top_n = config.get("similar_posts_count", 10)  # Default to 10 if not specified
    top_n = custom_top_n if custom_top_n > 0 else top_n
    
    query_embedding = calculate_embedding(query)
    
    results = []
    for post in all_posts:
        # Check if we have a cached embedding
        cached_embedding = None
        if post.id in embeddings_cache:
            cached_embedding = embeddings_cache[post.id]
        
        if cached_embedding is None:
            # Calculate and cache the embedding
            embedding = calculate_embedding(post.title + " " + post.content[:5000])
            embeddings_cache[post.id] = embedding
        else:
            embedding = cached_embedding
        
        # Calculate similarity (cosine similarity)
        similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
        results.append((post, float(similarity)))
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results[:top_n]


async def get_all_content(refresh: bool = False) -> Dict[str, List[Post]]:
    """Fetch content from all configured platforms with permanent caching."""
    config = load_config()
    cache_duration = timedelta(minutes=config.get("cache_duration_minutes", 60 * 24 * 7))  # Default to 1 week
    now = datetime.now()
    results = {}
    
    # Store the key for each post ID to identify platform
    post_sources = {}
    
    # Keep track of new or changed posts
    new_posts = {}
    
    # Check if we need to refresh any platforms
    platforms_to_fetch = []
    for platform in config.get("platforms", []):
        platform_type = platform.get("type")
        platform_url = platform.get("url")
        platform_name = platform.get("name", platform_url)
        
        cache_key = f"{platform_type}:{platform_url}"
        
        # Check if we need to refresh
        last_fetch_time = posts_cache.get(f"{cache_key}:last_fetch_time")
        
        if refresh or last_fetch_time is None or (now - last_fetch_time) > cache_duration:
            platforms_to_fetch.append((platform_type, platform_url, platform_name, cache_key))
        else:
            # Load posts from cache based on cache key
            platform_post_ids = posts_cache.get(f"{cache_key}:post_ids", [])
            platform_posts = []
            
            for post_id in platform_post_ids:
                post_data = posts_cache.get(f"post:{post_id}")
                if post_data:
                    post = Post.from_dict(post_data)
                    platform_posts.append(post)
                    post_sources[post_id] = cache_key
            
            results[platform_name] = platform_posts
    
    # Fetch content for platforms that need updating
    for platform_type, platform_url, platform_name, cache_key in platforms_to_fetch:
        try:
            max_posts = config.get("max_posts", 100)  # Default to higher limit
            
            if platform_type == "substack":
                posts = await fetch_substack_posts(platform_url, max_posts, platform_name)
            elif platform_type == "medium":
                posts = await fetch_medium_posts(platform_url, max_posts, platform_name)
            else:
                logger.warning(f"Unknown platform type: {platform_type}")
                continue
            
            # Update cache
            post_ids = []
            for post in posts:
                post_id = post.id
                post_ids.append(post_id)
                post_sources[post_id] = cache_key
                
                # Cache the post
                posts_cache[f"post:{post_id}"] = post.to_dict()
                
                # Mark as new/changed post
                new_posts[post_id] = post
            
            # Update the list of post IDs for this platform
            posts_cache[f"{cache_key}:post_ids"] = post_ids
            
            # Update the last fetch time
            posts_cache[f"{cache_key}:last_fetch_time"] = now
            
            results[platform_name] = posts
            
        except Exception as e:
            logger.error(f"Error fetching content from {platform_type}: {str(e)}")
            # Try to load from cache if available
            platform_post_ids = posts_cache.get(f"{cache_key}:post_ids", [])
            platform_posts = []
            
            for post_id in platform_post_ids:
                post_data = posts_cache.get(f"post:{post_id}")
                if post_data:
                    post = Post.from_dict(post_data)
                    platform_posts.append(post)
            
            if platform_posts:
                results[platform_name] = platform_posts
    
    # Generate embeddings for new/changed posts
    for post_id, post in new_posts.items():
        if post_id not in embeddings_cache:
            # Generate and cache the embedding
            logger.info(f"Generating embedding for: {post.title}")
            embedding = calculate_embedding(post.title + " " + post.content[:5000])
            embeddings_cache[post_id] = embedding
    
    return results


def get_all_posts() -> List[Post]:
    """Get a flat list of all posts from all platforms."""
    all_posts = []
    
    # Find all post IDs that we have cached
    for key in posts_cache:
        if key.startswith("post:"):
            post_id = key.split(":", 1)[1]
            post_data = posts_cache.get(key)
            if post_data:
                post = Post.from_dict(post_data)
                all_posts.append(post)
    
    return all_posts


# Expose individual essays as resources
@mcp.resource(r"mcp://writer-tool/essays")
async def essays() -> list:
    """Provide individual essays as resources."""
    all_posts = get_all_posts()
    resources = []
    
    for post in all_posts:
        post_uri = f"mcp://writer-tool/essay/{post.id}"
        resources.append({
            "uri": post_uri,
            "name": post.title,
            "description": f"{post.platform_name} - {post.date.strftime('%b %d, %Y') if post.date else 'Unknown date'}",
            "mime_type": "text/markdown"
        })
    
    return resources


@mcp.resource(r"mcp://writer-tool/essay/{post_id}")
async def essay(post_id: str) -> str:
    """Return a specific essay."""
    post_data = posts_cache.get(f"post:{post_id}")
    
    if not post_data:
        return f"Essay with ID {post_id} not found."
    
    post = Post.from_dict(post_data)
    
    # Format as markdown
    markdown = f"# {post.title}\n\n"
    
    if post.date:
        markdown += f"Date: {post.date.strftime('%b %d, %Y')}\n\n"
    
    markdown += f"Source: [{post.platform_name}]({post.url})\n\n"
    markdown += f"Word count: {post.word_count}\n\n"
    markdown += "---\n\n"
    markdown += post.content
    
    return markdown


@mcp.tool()
async def refresh_content() -> str:
    """
    Force refresh all content from configured platforms.
    
    This retrieves the latest posts and updates the cache.
    """
    results = await get_all_content(refresh=True)
    
    total_posts = sum(len(posts) for posts in results.values())
    platforms = ", ".join(results.keys())
    
    return f"Successfully refreshed {total_posts} posts from {platforms}. All content is permanently cached and embedded for search."


@mcp.tool()
async def search_writing(query: str) -> str:
    """
    Search for specific topics or keywords in your writing.
    
    Args:
        query: The search term or topic to look for
    
    Returns:
        Most relevant essays matching your search, with links to access full content
    """
    # Make sure content is loaded first
    await get_all_content()
    
    # Get all posts
    all_posts = get_all_posts()
    
    # Load config to get the top_n value
    config = load_config()
    top_n = config.get("similar_posts_count", 10)  # Default to 10 if not specified
    
    # Find similar posts using embeddings
    similar_posts = find_similar_posts(query, all_posts, top_n=top_n)
    
    if not similar_posts:
        return f"No relevant matches found for '{query}'"
    
    # Format response
    response = f"# Search Results for '{query}'\n\n"
    
    # Create a summary section
    response += "## Summary of Relevant Essays\n\n"
    response += f"Here are the {len(similar_posts)} most relevant essays based on your search:\n\n"
    
    for i, (post, score) in enumerate(similar_posts, 1):
        resource_uri = f"mcp://writer-tool/essay/{post.id}"
        date_str = post.date.strftime("%b %d, %Y") if post.date else "Unknown date"
        
        response += f"{i}. **[{post.title}]({resource_uri})** - {date_str} - Relevance: {score:.2f}\n"
        response += f"   Source: [{post.platform_name}]({post.url})\n"
        response += f"   Words: {post.word_count}\n\n"
    
    response += "## How to Access Full Essays\n\n"
    response += "You can access the full text of any essay by clicking on its title in the list above.\n"
    response += "Or you can ask Claude to 'Show me the full text of [essay title]'.\n\n"
    
    # Add a preview of the top result
    if similar_posts:
        top_post, top_score = similar_posts[0]
        response += "## Preview of Top Result\n\n"
        response += f"### {top_post.title}\n"
        date_str = top_post.date.strftime("%b %d, %Y") if top_post.date else "Unknown date"
        response += f"Date: {date_str} | [Original Link]({top_post.url})\n\n"
        
        # Extract a snippet around where the query appears, if possible
        content = top_post.content.lower()
        query_lower = query.lower()
        
        if query_lower in content:
            index = content.find(query_lower)
            start = max(0, index - 100)
            end = min(len(content), index + len(query_lower) + 100)
            
            # Extract the snippet with proper casing
            if start > 0:
                snippet = "..." + top_post.content[start:end] + "..."
            else:
                snippet = top_post.content[start:end] + "..."
            
            response += f"{snippet}\n\n"
        else:
            # Just show the beginning of the content
            preview = ' '.join(top_post.content.split()[:150])
            if len(top_post.content.split()) > 150:
                preview += "... (content continues)"
            
            response += f"{preview}\n\n"
    
    return response


async def preload_all_content():
    """
    Preload all content and generate embeddings at startup.
    
    This function forces a refresh of all platform content and 
    ensures that embeddings are generated for all posts.
    """
    logger.info("Preloading all content and generating embeddings...")
    
    # Force refresh all content
    results = await get_all_content(refresh=True)
    
    # Get all posts
    all_posts = get_all_posts()
    
    # Generate embeddings for all posts
    for post in all_posts:
        if post.id not in embeddings_cache:
            logger.info(f"Generating embedding for: {post.title}")
            embedding = calculate_embedding(post.title + " " + post.content[:5000])
            embeddings_cache[post.id] = embedding
    
    total_posts = sum(len(posts) for posts in results.values())
    platforms = ", ".join(results.keys())
    
    logger.info(f"Successfully preloaded {total_posts} posts from {platforms}")
    logger.info(f"Generated embeddings for {len(all_posts)} total posts")


if __name__ == "__main__":
    # Preload all content before starting server
    asyncio.run(preload_all_content())
    
    # Run the server
    mcp.run(transport="stdio") 