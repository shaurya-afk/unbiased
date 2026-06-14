from urllib.parse import parse_qs

from mcp_tools.tools import current_user_id, mcp
from services.database import get_user_by_token

_mcp_http_app = mcp.http_app(path="/")


class MCPAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            token = None

            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth.startswith("Bearer "):
                token = auth[7:].strip()

            if not token:
                qs = scope.get("query_string", b"").decode()
                params = parse_qs(qs)
                token_list = params.get("token", [])
                if token_list:
                    token = token_list[0]

            if token:
                uid = await get_user_by_token(token)
                if uid is not None:
                    current_user_id.set(uid)

        await self.app(scope, receive, send)


mcp_asgi_app = MCPAuthMiddleware(_mcp_http_app)
mcp_lifespan = _mcp_http_app.lifespan
