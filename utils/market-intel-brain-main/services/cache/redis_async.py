import aioredis
import json

class MAIFACache:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True
            )

    async def set(self, key: str, value: dict, ttl: int = 300):
        await self.connect()
        await self.redis.set(key, json.dumps(value), ex=ttl)

    async def get(self, key: str):
        await self.connect()
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def exists(self, key: str):
        await self.connect()
        return await self.redis.exists(key)

cache = MAIFACache()
