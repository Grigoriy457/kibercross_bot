from typing import List, Dict, Optional, TYPE_CHECKING
import datetime

import enum
from sqlalchemy import Column, BIGINT, String, Boolean, DateTime, func, Integer, ForeignKey, Enum, JSON
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, relationship

from database.models.base import Base
if TYPE_CHECKING:
    from database.models.registration import Registration


__all__ = [
    "Admin",
    "FsmData",
    "TgUser",
]


class Admin(Base):
    __tablename__ = "admin"

    created_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    tg_user_id: Mapped[int] = Column(BIGINT, ForeignKey("tg_user.id", ondelete='CASCADE'), primary_key=True, nullable=False)
    name: Mapped[str] = Column(String(100), nullable=False)
    is_disabled: Mapped[bool] = Column(Boolean, nullable=False, default=0)

    tg_user: Mapped["TgUser"] = relationship("TgUser")


class TgUser(Base):
    __tablename__ = "tg_user"

    created_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    id: Mapped[int] = Column(BIGINT, primary_key=True, nullable=False)
    username: Mapped[str] = Column(String(32))
    is_policy_confirmed: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    is_disabled: Mapped[bool] = Column(Boolean, nullable=False, default=0)

    registration: Mapped["Registration"] = relationship("Registration", back_populates="tg_user")

    def __repr__(self):
        return f"<TgUser: id={self.id}, username={self.username}, is_disabled={self.is_disabled}>"


class FsmData(Base):
    __tablename__ = "fsm_data"
    __table_args__ = (
        UniqueConstraint('chat_id', 'user_id'),
    )

    created_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    id: Mapped[int] = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    chat_id: Mapped[int] = Column(BIGINT, nullable=False)
    user_id: Mapped[int] = Column(BIGINT, ForeignKey("tg_user.id", ondelete='CASCADE'), nullable=False)
    state: Mapped[Optional[str]] = Column(String(100))
    data: Mapped[Dict] = Column(JSON, nullable=False, default=lambda: {})

    def __repr__(self):
        return f"<FsmData: id={self.id}, chat_id={self.chat_id}, user_id={self.user_id}, state={self.state}, data=...>"
