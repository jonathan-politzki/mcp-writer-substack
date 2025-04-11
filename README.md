# Writer Context Tool for Claude

A Model Context Protocol (MCP) implementation that connects Claude to your Substack and Medium writing.

## What is this?

Writer Context Tool is an MCP server that allows Claude to access and analyze your writing from platforms like Substack and Medium. With this tool, Claude can understand the context of your published content, providing more personalized assistance with your writing.

## Features

- 🔍 Retrieves and permanently caches your blog posts from Substack and Medium
- 🔎 Uses embeddings to find the most relevant essays based on your queries
- 📚 Makes individual essays available as separate resources for Claude
- 🧠 Performs semantic searches across your writing
- ⚡ Preloads all content and generates embeddings at startup

## How It Works

The tool connects to your Substack/Medium blogs via their RSS feeds, fetches your posts, and permanently caches them locally. It also generates embeddings for each post, enabling semantic search to find the most relevant essays based on your queries.

When you ask Claude about your writing, it can use these individual essay resources to provide insights or help you develop new ideas based on your existing content.

## Setup Instructions (Step by Step)

### Prerequisites

- Python 3.10 or higher
- Claude Desktop (latest version)
- A Substack or Medium account with published content

### 1. Clone this Repository

```bash
git clone https://github.com/yourusername/writer-context-tool.git
cd writer-context-tool
```

### 2. Set up Python Environment

Using uv (recommended):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Or using standard pip:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Your Blogs

1. Copy the example configuration file:
   ```bash
   cp config.example.json config.json
   ```

2. Edit `config.json` with your Substack/Medium URLs:
   ```json
   {
     "platforms": [
       {
         "type": "substack",
         "url": "https://yourusername.substack.com",
         "name": "My Substack Blog"
       },
       {
         "type": "medium",
         "url": "https://medium.com/@yourusername",
         "name": "My Medium Blog"
       }
     ],
     "max_posts": 100,
     "cache_duration_minutes": 10080,
     "similar_posts_count": 10
   }
   ```
   
   - `max_posts`: Maximum number of posts to fetch from each platform (default: 100)
   - `cache_duration_minutes`: How long to cache content before refreshing (default: 1 week or 10080 minutes)
   - `similar_posts_count`: Number of most relevant posts to return when searching (default: 10)

### 4. Connect with Claude Desktop

1. Create the Claude Desktop configuration directory:
   ```bash
   # On macOS
   mkdir -p ~/Library/Application\ Support/Claude/
   ```

2. Create the configuration file:
   ```bash
   # Get the absolute path to your uv command
   UV_PATH=$(which uv)
   
   # Create the configuration
   cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << EOF
   {
     "mcpServers": {
       "writer-tool": {
         "command": "${UV_PATH}",
         "args": [
           "--directory",
           "$(pwd)",
           "run",
           "writer_tool.py"
         ]
       }
     }
   }
   EOF
   ```
   
   > **Note:** If you experience issues with the `uv` command, you can use the included shell script alternative:
   > 1. Make the script executable: `chmod +x run_writer_tool.sh`
   > 2. Update your Claude Desktop config to use the script:
   > ```json
   > {
   >   "mcpServers": {
   >     "writer-tool": {
   >       "command": "/absolute/path/to/run_writer_tool.sh",
   >       "args": []
   >     }
   >   }
   > }
   > ```

3. Restart Claude Desktop

## Using the Tool with Claude

Once set up, you'll see individual essays available as resources in Claude Desktop. You can:

1. **Search across your writing**: Ask Claude to find relevant content
   - "Find essays where I discuss [specific topic]"
   - "What have I written about [subject]?"

2. **Reference specific essays**: Access individual essays by clicking on them when listed in search results
   - "Show me the full text of [essay title]"

3. **Refresh content**: Force a refresh of your content
   - "Refresh my writing content"

## Available Tools and Resources

The Writer Context Tool provides:

1. **Individual Essay Resources**: Each of your essays becomes a selectable resource
2. **search_writing**: A semantic search tool that finds the most relevant essays using embeddings
3. **refresh_content**: Refreshes and recaches your content from all configured platforms

## How Caching Works

The tool implements permanent caching with these features:

1. **Disk Caching**: All content is stored on disk, so it persists between sessions
2. **Embeddings**: Each essay is converted to embeddings for semantic search
3. **Selective Refresh**: The tool only refreshes content when needed according to your cache settings
4. **Preloading**: All content is automatically refreshed and embeddings generated at startup

## Troubleshooting

If you encounter issues:

1. **Tool doesn't appear in Claude Desktop:**
   - Check that your Claude Desktop configuration file is correct
   - Verify that all paths in the configuration are absolute 
   - Make sure your Python environment has all required packages
   - Restart Claude Desktop

2. **No content appears:**
   - Verify your Substack/Medium URLs in config.json
   - Try using the "refresh_content" tool
   - Check that your blogs are public and have published posts

3. **Error with uv command:**
   - Try using the shell script approach instead
   - Verify the uv command is installed and in your PATH

4. **Embedding issues:**
   - If you see errors about the embedding model, make sure you have enough disk space
   - Consider rerunning with a fresh installation if embeddings aren't working properly

## License

This project is available under the MIT License. 