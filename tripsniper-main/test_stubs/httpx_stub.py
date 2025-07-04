class Response:
    def __init__(self, data=None, status_code=200):
        self._data = data or {}
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class AsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def request(self, *args, **kwargs):  # pragma: no cover - simple stub
        return Response()

    async def get(self, *args, **kwargs):  # pragma: no cover - simple stub
        return await self.request("GET", *args, **kwargs)

    async def post(self, *args, **kwargs):  # pragma: no cover - simple stub
        return await self.request("POST", *args, **kwargs)
