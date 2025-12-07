# Erised

**Visual Memory for AI** - Store and search images using semantic embeddings.

## Installation

```bash
pip install git+https://github.com/exla-ai/erised.git
```

## Quick Start

```python
from erised import ErisedClient

# Initialize with your API key
client = ErisedClient(api_key="your-api-key")

# Add an image to memory
result = client.add(
    image="screenshot.png",
    user_id="user123",
    metadata={"app": "vscode"}
)
print(f"Added memory: {result['memory_id']}")

# Search by natural language
results = client.search(
    "code editor with dark theme",
    user_id="user123"
)

for r in results["results"]:
    print(f"{r['memory_id']}: {r['score']:.2f}")
```

## Features

- **Semantic Search**: Find images by describing what you're looking for
- **User Isolation**: Data is isolated by `user_id` for multi-tenant apps
- **Simple API**: Add, search, list, get, and delete memories
- **Async Support**: Use `AsyncErisedClient` for async/await

## API Reference

### `ErisedClient`

```python
client = ErisedClient(
    api_key="your-api-key",  # Required
    timeout=120.0            # Optional, default 120s
)
```

### Methods

| Method | Description |
|--------|-------------|
| `add(image, user_id, metadata=None)` | Add an image to memory |
| `search(query, user_id=None, top_k=10)` | Search memories by text |
| `list(user_id=None, limit=100)` | List all memories |
| `get(memory_id)` | Get a specific memory |
| `get_image(memory_id)` | Get image bytes |
| `delete(memory_id)` | Delete a memory |
| `health()` | Check API status |

## Documentation

Full documentation at [erised.exla.ai/docs](https://erised.exla.ai/docs)

## License

MIT
