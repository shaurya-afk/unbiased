import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    github_username: Mapped[str] = mapped_column(String, unique=True)
    github_token: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RawGithubData(Base):
    __tablename__ = "raw_github_data"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    repos_json: Mapped[Any] = mapped_column(JSON)
    languages_json: Mapped[Any] = mapped_column(JSON)
    readmes_json: Mapped[Any] = mapped_column(JSON)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ContextFile(Base):
    __tablename__ = "context_files"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    filename: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserToken(Base):
    __tablename__ = "user_tokens"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    mcp_token: Mapped[str] = mapped_column(String, unique=True)


engine = create_async_engine(os.environ["DATABASE_URL"])
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def upsert_user(username: str, token: str) -> int:
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        stmt = (
            pg_insert(User)
            .values(github_username=username, github_token=token, created_at=now)
            .on_conflict_do_update(
                index_elements=["github_username"],
                set_={"github_token": token},
            )
            .returning(User.id)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()


async def store_raw_data(user_id: int, repos: list, languages: dict, readmes: dict):
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        stmt = (
            pg_insert(RawGithubData)
            .values(
                user_id=user_id,
                repos_json=repos,
                languages_json=languages,
                readmes_json=readmes,
                extracted_at=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "repos_json": repos,
                    "languages_json": languages,
                    "readmes_json": readmes,
                    "extracted_at": now,
                },
            )
        )
        await session.execute(stmt)
        await session.commit()


async def get_raw_data(user_id: int) -> Optional[RawGithubData]:
    async with async_session() as session:
        result = await session.execute(
            select(RawGithubData).where(RawGithubData.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def upsert_context_file(user_id: int, filename: str, content: str):
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        stmt = (
            pg_insert(ContextFile)
            .values(user_id=user_id, filename=filename, content=content, generated_at=now)
            .on_conflict_do_update(
                index_elements=["user_id", "filename"],
                set_={"content": content, "generated_at": now},
            )
        )
        await session.execute(stmt)
        await session.commit()


async def get_context_files(user_id: int) -> list[ContextFile]:
    async with async_session() as session:
        result = await session.execute(
            select(ContextFile).where(ContextFile.user_id == user_id)
        )
        return list(result.scalars().all())


async def upsert_user_token(user_id: int) -> str:
    async with async_session() as session:
        result = await session.execute(
            select(UserToken).where(UserToken.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing.mcp_token
        token = str(uuid.uuid4())
        session.add(UserToken(user_id=user_id, mcp_token=token))
        await session.commit()
        return token


async def get_user_by_token(token: str) -> Optional[int]:
    async with async_session() as session:
        result = await session.execute(
            select(UserToken).where(UserToken.mcp_token == token)
        )
        row = result.scalar_one_or_none()
        return row.user_id if row else None
