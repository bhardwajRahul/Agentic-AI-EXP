import asyncio


async def chat_chunker(chat_history, chunk_min_size=256, chunk_max_size=512):
    """Chunk the chat history into smaller pieces."""
