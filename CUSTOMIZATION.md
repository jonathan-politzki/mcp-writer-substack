# Customizing the Writer Context Tool

This document explains how to customize the Writer Context Tool to better suit your needs, especially if you want to pull more content or customize how it works.

## Fine-Tuning the Content Cache

The tool now implements permanent caching to disk and uses embeddings for semantic search. Here's how you can customize this behavior:

### Increasing Content Limits

The default configuration now fetches up to 100 posts from each platform. If you want to adjust this:

```json
{
  "platforms": [
    ...
  ],
  "max_posts": 200,  // Increase from default of 100
  "cache_duration_minutes": 10080,  // One week (7 days)
  "similar_posts_count": 15  // Increase from default of 10
}
```

You can set `max_posts` as high as needed, but be aware that:
- Fetching many posts will take longer during refresh
- Each post requires storage for both content and embeddings
- Very large numbers of posts may impact Claude's resource selection UI

### Customizing Context Retrieval

The tool now includes a `similar_posts_count` parameter that controls how many related essays are returned for each query:

```json
{
  "platforms": [
    ...
  ],
  "similar_posts_count": 15  // Return 15 most relevant essays instead of default 10
}
```

This parameter affects:
- The number of essays shown in search results
- The amount of context Claude can reference when answering your questions
- The processing time needed for each search (higher values might be slightly slower)

### Automatic Preloading at Startup

The tool now automatically preloads all content and generates all embeddings at startup. This means:

1. Your content will be refreshed when you start the tool
2. All embeddings will be generated immediately, making searches faster
3. Claude will have access to your entire writing corpus from the start

You can modify this behavior by editing the `preload_all_content` function in `writer_tool.py` if you want to:

- Make preloading optional
- Run it on a periodic schedule instead of just at startup
- Add filtering to only preload certain platforms

### Customizing Embedding Generation

The tool uses the `all-MiniLM-L6-v2` model from sentence-transformers for embeddings. Advanced users can modify this in the code:

1. Open `writer_tool.py` and find the `get_embedding_model` function
2. Change the model name to any valid sentence-transformers model:

```python
def get_embedding_model():
    global model
    if model is None:
        logger.info("Loading embedding model...")
        # Change to a different model if needed
        model = SentenceTransformer('all-mpnet-base-v2')  # Higher quality but slower
        logger.info("Embedding model loaded")
    return model
```

Some alternative models:
- `all-mpnet-base-v2`: Higher quality embeddings but slower
- `all-MiniLM-L12-v2`: Better quality than L6 with moderate speed
- `paraphrase-multilingual-MiniLM-L12-v2`: For multi-language support

## Adding More Content Sources

The tool currently supports Substack and Medium. To add support for other platforms:

1. Study how the existing scrapers work in `writer_tool.py`
2. Implement a new scraper function similar to `fetch_substack_posts`
3. Update the `get_all_content` function to support your new platform type

Example for adding WordPress support:

```python
async def fetch_wordpress_posts(url: str, max_posts: int, platform_name: str) -> List[Post]:
    """Fetch posts from a WordPress blog."""
    try:
        logger.info(f"Fetching WordPress posts from: {url}")
        # Ensure URL ends with slash
        if not url.endswith("/"):
            url += "/"
            
        rss_url = f"{url}feed"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(rss_url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            logger.info(f"Found {len(feed.entries)} WordPress posts")
            
        # Rest of implementation...
    except Exception as e:
        logger.error(f"Error fetching WordPress feed: {str(e)}")
        return []
    
    # Process posts similar to the other scrapers...
```

Then add it to the `get_all_content` function:

```python
if platform_type == "substack":
    posts = await fetch_substack_posts(platform_url, max_posts, platform_name)
elif platform_type == "medium":
    posts = await fetch_medium_posts(platform_url, max_posts, platform_name)
elif platform_type == "wordpress":  # Add this section
    posts = await fetch_wordpress_posts(platform_url, max_posts, platform_name)
else:
    logger.warning(f"Unknown platform type: {platform_type}")
    continue
```

## Customizing Search Behavior

The tool now uses semantic search instead of keyword matching. You can customize the search behavior:

### Adjusting Similarity Thresholds

In the `find_similar_posts` function, you can adjust the number of results or add a similarity threshold:

```python
def find_similar_posts(query: str, all_posts: List[Post], top_n: int = 5, min_similarity: float = 0.3) -> List[Tuple[Post, float]]:
    """Find posts similar to the query using embeddings."""
    # ... existing code ...
    
    # Add a minimum similarity threshold
    results = [(post, sim) for post, sim in results if sim >= min_similarity]
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results[:top_n]
```

### Hybrid Search

For advanced users, you could implement a hybrid search that combines semantic search with keyword matching:

```python
def hybrid_search(query: str, all_posts: List[Post], top_n: int = 5) -> List[Tuple[Post, float]]:
    """Combine semantic search with keyword matching."""
    # Semantic search results
    semantic_results = find_similar_posts(query, all_posts, top_n=top_n*2)
    
    # Keyword matching (simple implementation)
    query_lower = query.lower()
    keyword_matches = []
    for post in all_posts:
        if query_lower in post.title.lower() or query_lower in post.content.lower():
            # Give exact matches a high score
            keyword_matches.append((post, 0.95))
    
    # Combine results (with duplicates removed)
    seen_ids = set()
    combined_results = []
    
    # First add exact matches
    for post, score in keyword_matches:
        if post.id not in seen_ids:
            combined_results.append((post, score))
            seen_ids.add(post.id)
    
    # Then add semantic matches
    for post, score in semantic_results:
        if post.id not in seen_ids:
            combined_results.append((post, score))
            seen_ids.add(post.id)
            
    return combined_results[:top_n]
```

## Advanced: Optimizing Performance

For large collections of essays or improved performance:

### Persistent Embedding Cache

The tool already implements disk caching, but you might want to customize its behavior:

```python
# Initialize with a custom max_size
embeddings_cache = Cache(str(cache_dir / "embeddings"), size_limit=1_000_000_000)  # 1GB limit
```

### Background Content Refresh

You could implement a background refresh mechanism:

```python
async def background_refresh():
    """Refresh content in the background."""
    while True:
        try:
            await get_all_content(refresh=True)
            logger.info("Background refresh completed successfully")
        except Exception as e:
            logger.error(f"Error in background refresh: {str(e)}")
        
        # Wait for next refresh cycle
        await asyncio.sleep(3600)  # 1 hour

# Start background refresh
asyncio.create_task(background_refresh())
```

## Debugging Tips

If you're customizing the tool and need to debug:

1. **Increase Logging Detail**:
   ```python
   logging.basicConfig(
       level=logging.DEBUG,  # Change from INFO to DEBUG
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
   )
   ```

2. **Inspect Cache Contents**:
   You can use the following code to inspect cache contents:
   ```python
   for key in posts_cache:
       print(f"Cache key: {key}")
   ```

3. **Testing Embeddings**:
   To test if embeddings are working correctly:
   ```python
   test_embedding = calculate_embedding("This is a test")
   print(f"Embedding shape: {test_embedding.shape}")
   ``` 