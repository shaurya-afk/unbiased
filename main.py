import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

load_dotenv()

from services.database import init_db
from routers import auth, dashboard
from routers.mcp import mcp_asgi_app, mcp_lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_lifespan(app):
        await init_db()
        yield


app = FastAPI(title="unbiased", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET_KEY"])
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.mount("/mcp", mcp_asgi_app)
