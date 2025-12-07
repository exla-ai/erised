"""
Erised Client - Python SDK for Erised Visual Memory API

Usage:
    from erised import ErisedClient
    
    client = ErisedClient(api_key="your-api-key")
    
    # Add an image memory
    result = client.add(
        image="path/to/screenshot.png",
        user_id="user123"
    )
    
    # Search memories
    results = client.search("code editor", user_id="user123")
"""

import os
import json
import httpx
from pathlib import Path
from typing import Optional, Union, BinaryIO


# Default API endpoint
DEFAULT_API_URL = "https://viraat--erised-erisedapi-serve.modal.run"


class ErisedClient:
    """
    Client for interacting with the Erised Visual Memory API.
    
    Args:
        api_key: Your Erised API key. If not provided, reads from ERISED_API_KEY env var.
        api_url: Base URL for the API. Defaults to the Erised API endpoint.
        timeout: Request timeout in seconds. Defaults to 120 (model inference can be slow).
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("ERISED_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Pass api_key parameter or set ERISED_API_KEY environment variable."
            )
        
        self.api_url = (api_url or os.environ.get("ERISED_API_URL", DEFAULT_API_URL)).rstrip("/")
        self.timeout = timeout
        
        self._client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "erised-python/0.1.0",
            },
            timeout=timeout,
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def add(
        self,
        image: Union[str, Path, bytes, BinaryIO],
        user_id: str,
        metadata: Optional[dict] = None,
        memory_id: Optional[str] = None,
    ) -> dict:
        """
        Add an image to visual memory.
        
        Args:
            image: Image to store. Can be:
                - Path to image file (str or Path)
                - Raw image bytes
                - File-like object with read() method
            user_id: User identifier for memory isolation
            metadata: Optional metadata to store with the memory
            memory_id: Optional custom ID for the memory (auto-generated if not provided)
        
        Returns:
            dict with memory_id and confirmation message
        
        Example:
            >>> result = client.add("screenshot.png", user_id="user123")
            >>> print(result["memory_id"])
        """
        # Prepare the image data
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {path}")
            with open(path, "rb") as f:
                image_data = f.read()
            filename = path.name
        elif isinstance(image, bytes):
            image_data = image
            filename = "image.png"
        elif hasattr(image, "read"):
            image_data = image.read()
            filename = getattr(image, "name", "image.png")
            if isinstance(filename, str) and "/" in filename:
                filename = filename.split("/")[-1]
        else:
            raise TypeError(f"Invalid image type: {type(image)}")
        
        # Build multipart form data
        files = {"file": (filename, image_data, "image/png")}
        data = {"user_id": user_id}
        
        if metadata:
            data["metadata"] = json.dumps(metadata)
        
        if memory_id:
            data["memory_id"] = memory_id
        
        response = self._client.post("/v1/memories/add", files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        filters: Optional[dict] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
    ) -> dict:
        """
        Search visual memories by text query.
        
        Args:
            query: Natural language search query
            user_id: Filter by user ID (can also be in filters)
            filters: Additional filters (e.g., {"user_id": "user123"})
            top_k: Maximum number of results to return
            score_threshold: Minimum similarity score (optional)
        
        Returns:
            dict with "results" list containing matching memories
        
        Example:
            >>> results = client.search("code editor", user_id="user123")
            >>> for r in results["results"]:
            ...     print(f"{r['memory_id']}: {r['score']}")
        """
        payload = {
            "query": query,
            "top_k": top_k,
        }
        
        # Handle filters
        if filters is None:
            filters = {}
        if user_id:
            filters["user_id"] = user_id
        if filters:
            payload["filters"] = filters
        
        if score_threshold is not None:
            payload["score_threshold"] = score_threshold
        
        response = self._client.post("/v1/memories/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get(self, memory_id: str) -> dict:
        """
        Get a specific memory by ID.
        
        Args:
            memory_id: The memory ID to retrieve
        
        Returns:
            Memory object with metadata including image_url
        """
        response = self._client.get(f"/v1/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    
    def get_image(self, memory_id: str) -> bytes:
        """
        Get the image bytes for a specific memory.
        
        Args:
            memory_id: The memory ID to retrieve the image for
        
        Returns:
            Image bytes that can be written to file or used with PIL
        
        Example:
            >>> image_bytes = client.get_image("abc-123")
            >>> with open("output.png", "wb") as f:
            ...     f.write(image_bytes)
        """
        memory = self.get(memory_id)
        image_url = memory.get("image_url")
        if not image_url:
            raise ValueError(f"No image_url found for memory {memory_id}")
        
        response = self._client.get(image_url)
        response.raise_for_status()
        return response.content
    
    def get_image_url(self, memory_id: str) -> str:
        """
        Get the full image URL for a specific memory.
        
        Args:
            memory_id: The memory ID
        
        Returns:
            Full URL to the image (requires auth header to access)
        """
        memory = self.get(memory_id)
        image_url = memory.get("image_url")
        if not image_url:
            raise ValueError(f"No image_url found for memory {memory_id}")
        return f"{self.api_url}{image_url}"
    
    def list(
        self,
        user_id: Optional[str] = None,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        List memories, optionally filtered by user.
        
        Args:
            user_id: Filter by user ID
            filters: Additional filters
            limit: Maximum results to return
            offset: Pagination offset
        
        Returns:
            dict with "memories" list and pagination info
        """
        params = {"limit": limit, "offset": offset}
        
        if user_id:
            params["user_id"] = user_id
        
        response = self._client.get("/v1/memories", params=params)
        response.raise_for_status()
        return response.json()
    
    def delete(self, memory_id: str) -> dict:
        """
        Delete a memory by ID.
        
        Args:
            memory_id: The memory ID to delete
        
        Returns:
            Confirmation message
        """
        response = self._client.delete(f"/v1/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    
    def health(self) -> dict:
        """
        Check API health status.
        
        Returns:
            Health status information
        """
        response = self._client.get("/health")
        response.raise_for_status()
        return response.json()


class AsyncErisedClient:
    """
    Async client for interacting with the Erised Visual Memory API.
    
    Usage:
        async with AsyncErisedClient(api_key="your-key") as client:
            results = await client.search("code editor", user_id="user123")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("ERISED_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Pass api_key parameter or set ERISED_API_KEY environment variable."
            )
        
        self.api_url = (api_url or os.environ.get("ERISED_API_URL", DEFAULT_API_URL)).rstrip("/")
        self.timeout = timeout
        
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "erised-python/0.1.0",
            },
            timeout=timeout,
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def add(
        self,
        image: Union[str, Path, bytes, BinaryIO],
        user_id: str,
        metadata: Optional[dict] = None,
        memory_id: Optional[str] = None,
    ) -> dict:
        """Add an image to visual memory (async version)."""
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {path}")
            with open(path, "rb") as f:
                image_data = f.read()
            filename = path.name
        elif isinstance(image, bytes):
            image_data = image
            filename = "image.png"
        elif hasattr(image, "read"):
            image_data = image.read()
            filename = getattr(image, "name", "image.png")
        else:
            raise TypeError(f"Invalid image type: {type(image)}")
        
        files = {"file": (filename, image_data, "image/png")}
        data = {"user_id": user_id}
        
        if metadata:
            data["metadata"] = json.dumps(metadata)
        
        if memory_id:
            data["memory_id"] = memory_id
        
        response = await self._client.post("/v1/memories/add", files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        filters: Optional[dict] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
    ) -> dict:
        """Search visual memories by text query (async version)."""
        payload = {"query": query, "top_k": top_k}
        
        if filters is None:
            filters = {}
        if user_id:
            filters["user_id"] = user_id
        if filters:
            payload["filters"] = filters
        
        if score_threshold is not None:
            payload["score_threshold"] = score_threshold
        
        response = await self._client.post("/v1/memories/search", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get(self, memory_id: str) -> dict:
        """Get a specific memory by ID (async version)."""
        response = await self._client.get(f"/v1/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_image(self, memory_id: str) -> bytes:
        """Get the image bytes for a specific memory (async version)."""
        memory = await self.get(memory_id)
        image_url = memory.get("image_url")
        if not image_url:
            raise ValueError(f"No image_url found for memory {memory_id}")
        
        response = await self._client.get(image_url)
        response.raise_for_status()
        return response.content
    
    async def get_image_url(self, memory_id: str) -> str:
        """Get the full image URL for a specific memory (async version)."""
        memory = await self.get(memory_id)
        image_url = memory.get("image_url")
        if not image_url:
            raise ValueError(f"No image_url found for memory {memory_id}")
        return f"{self.api_url}{image_url}"
    
    async def list(
        self,
        user_id: Optional[str] = None,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """List memories (async version)."""
        params = {"limit": limit, "offset": offset}
        
        if user_id:
            params["user_id"] = user_id
        
        response = await self._client.get("/v1/memories", params=params)
        response.raise_for_status()
        return response.json()
    
    async def delete(self, memory_id: str) -> dict:
        """Delete a memory by ID (async version)."""
        response = await self._client.delete(f"/v1/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    
    async def health(self) -> dict:
        """Check API health status (async version)."""
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

