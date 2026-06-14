from urllib.parse import parse_qs

from mcp_tools.tools import current_user_id, mcp
from services.database import get_user_by_token


class MCPAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            token = None

            # 1. Authorization: Bearer header
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth.startswith("Bearer "):
                token = auth[7:].strip()

            # 2. ?token= query parameter
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


def build_mcp_app():
    return MCPAuthMiddleware(mcp.http_app())
