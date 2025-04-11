# Detailed Setup Guide for Writer Context Tool

This guide will walk you through setting up the Writer Context Tool for Claude step by step.

## How to Use This Tool as a New User

As a new user, here's how you would set up and use this tool:

1. **Fork or clone the repository** to your local machine
2. **Configure it** with your own blog URLs
3. **Connect it** to Claude Desktop
4. **Start using it** to access individual essays and search your writing

## Detailed Setup Process

### 1. Get the Code

First, clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/writer-context-tool.git
cd writer-context-tool
```

### 2. Set Up Python Environment

Next, set up a Python virtual environment and install dependencies:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

### 3. Configure Your Blogs

1. Create your configuration file:

```bash
cp config.example.json config.json
```

2. Edit `config.json` with your own blog URLs:

```json
{
  "platforms": [
    {
      "type": "substack",
      "url": "https://yourusername.substack.com",
      "name": "My Substack Blog"
    }
  ],
  "max_posts": 100,
  "cache_duration_minutes": 10080
}
```

You can add multiple platforms, including Medium:

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
  "cache_duration_minutes": 10080
}
```

Configuration options:
- `max_posts`: Controls how many posts to fetch from each platform (default: 100)
- `cache_duration_minutes`: How long to cache content before refreshing (default: 1 week or 10080 minutes)

### 4. Connect to Claude Desktop

Claude Desktop uses a configuration file to know about available MCP tools. You need to:

1. Create the Claude Desktop configuration directory:

```bash
# On macOS
mkdir -p ~/Library/Application\ Support/Claude/
```

2. Find the absolute path to your `uv` command:

```bash
which uv
# Example output: /Users/yourusername/.local/bin/uv
```

3. Create the Claude Desktop configuration file:

```bash
# Create the configuration file with the absolute paths
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << EOF
{
  "mcpServers": {
    "writer-tool": {
      "command": "/absolute/path/to/uv",
      "args": [
        "--directory",
        "/absolute/path/to/writer-context-tool",
        "run",
        "writer_tool.py"
      ]
    }
  }
}
EOF
```

Be sure to replace:
- `/absolute/path/to/uv` with the actual path from the `which uv` command
- `/absolute/path/to/writer-context-tool` with the absolute path to where you cloned the repository

4. Restart Claude Desktop

### Using the Shell Script Alternative (if needed)

If you have issues with the `uv` method, use the shell script method:

1. Make the script executable:

```bash
chmod +x run_writer_tool.sh
```

2. Edit the Claude Desktop configuration:

```bash
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << EOF
{
  "mcpServers": {
    "writer-tool": {
      "command": "$(pwd)/run_writer_tool.sh",
      "args": []
    }
  }
}
EOF
```

## First Run: What to Expect

When you first start Claude Desktop after configuration:

1. The Writer Tool will connect to your blog(s) and fetch your posts
2. It will create a permanent cache of these posts on your local disk
3. It will generate embeddings for each post for semantic searching
4. Your essays will appear as individual resources in Claude Desktop

This initial setup might take a few minutes if you have many posts.

## How to Use the Tool with Claude

After setup, you can:

1. **Browse individual essays**: Each essay appears as a separate resource
2. **Search your writing**: Use the search_writing tool to find relevant essays
   - "Find essays related to [topic]"
   - "Search my writing for mentions of [concept]"
3. **Refresh your content**: Force a refresh when you publish new posts
   - "Refresh my writing content"

## Troubleshooting

If you don't see the tool in Claude Desktop:

1. Verify your configuration in the Claude Desktop settings
2. Check that all paths are absolute (full paths)
3. Make sure your Python environment is properly set up
4. Restart Claude Desktop

If content isn't loading correctly:

1. Use the "refresh_content" tool
2. Verify your blog URLs are correct
3. Check your `.cache` directory to ensure it has write permissions

If embedding search isn't working well:

1. Make sure sentence-transformers is properly installed
2. Try reinstalling the dependencies 