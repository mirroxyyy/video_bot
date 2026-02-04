from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class VideoOrm(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(primary_key=True)
    creator_id: Mapped[str]
    video_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    views_count: Mapped[int]
    likes_count: Mapped[int]
    comments_count: Mapped[int]
    reports_count: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        id_: str,
        creator_id: str,
        video_created_at: datetime,
        views_count: int,
        likes_count: int,
        comments_count: int,
        reports_count: int,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id_
        self.creator_id = creator_id
        self.video_created_at = video_created_at
        self.views_count = views_count
        self.likes_count = likes_count
        self.comments_count = comments_count
        self.reports_count = reports_count
        self.created_at = created_at
        self.updated_at = updated_at


class VideoSnapshotOrm(Base):
    __tablename__ = "video_snapshots"
    id: Mapped[str] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(ForeignKey(VideoOrm.id, ondelete="CASCADE"))
    views_count: Mapped[int]
    likes_count: Mapped[int]
    comments_count: Mapped[int]
    reports_count: Mapped[int]
    delta_views_count: Mapped[int]
    delta_likes_count: Mapped[int]
    delta_comments_count: Mapped[int]
    delta_reports_count: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        id_: str,
        video_id: str,
        views_count: int,
        likes_count: int,
        comments_count: int,
        reports_count: int,
        delta_views_count: int,
        delta_likes_count: int,
        delta_comments_count: int,
        delta_reports_count: int,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id_
        self.video_id = video_id
        self.views_count = views_count
        self.likes_count = likes_count
        self.comments_count = comments_count
        self.reports_count = reports_count
        self.delta_views_count = delta_views_count
        self.delta_likes_count = delta_likes_count
        self.delta_comments_count = delta_comments_count
        self.delta_reports_count = delta_reports_count
        self.created_at = created_at
        self.updated_at = updated_at
