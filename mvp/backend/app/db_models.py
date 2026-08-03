from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    families: Mapped[list["Family"]] = relationship(back_populates="owner")


class Family(Base):
    """A family is owned by exactly one user. There is no sharing model yet —
    ownership IS the isolation boundary. Every query that touches a Family or
    its Ancestors must filter by owner_user_id == current_user.id."""

    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped["User"] = relationship(back_populates="families")
    ancestors: Mapped[list["AncestorProfile"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )


class AncestorProfile(Base):
    __tablename__ = "ancestor_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    relation: Mapped[str] = mapped_column(String(100))
    birth_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    death_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    death_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text)
    generated_profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    family: Mapped["Family"] = relationship(back_populates="ancestors")
