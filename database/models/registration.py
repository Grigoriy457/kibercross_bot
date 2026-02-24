from contextlib import nullcontext
from email.policy import default
from typing import List, Dict, Optional, TYPE_CHECKING
import datetime
import pprint

import enum
from sqlalchemy import Column, BIGINT, String, Boolean, DateTime, Date, func, Integer, ForeignKey, event, Enum, JSON
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import Mapped, relationship, backref

from database.models.base import Base

if TYPE_CHECKING:
    from database.models.tg import TgUser, Admin


__all__ = [
    "Registration",
    "DisciplineEnum",
    "Team",
    "TeamMembers",
]


class Registration(Base):
    __tablename__ = "registration"

    created_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    id: Mapped[int] = Column(Integer, primary_key=True, nullable=False)
    tg_user_id: Mapped[int] = Column(BIGINT, ForeignKey("tg_user.id", ondelete='CASCADE'), unique=True, nullable=False)
    full_name: Mapped[str] = Column(String(100), nullable=False)
    from_bmstu: Mapped[bool] = Column(Boolean, nullable=False, default=1)
    phone_number: Mapped[Optional[str]] = Column(String(20))
    birthdate: Mapped[Optional[datetime.date]] = Column(Date, nullable=False)
    edu_group: Mapped[Optional[str]] = Column(String(10))
    university: Mapped[Optional[str]] = Column(String(300))
    passport_data: Mapped[Optional[str]] = Column(String(20))
    nickname: Mapped[Optional[str]] = Column(String(50))

    cs2_steam_id: Mapped[Optional[str]] = Column(String(32))
    cs2_faceit_nickname: Mapped[Optional[str]] = Column(String(70))
    cs2_is_bring_own_devices: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    dota2_steam_id: Mapped[Optional[str]] = Column(String(32))
    dota2_is_bring_own_devices: Mapped[bool] = Column(Boolean, nullable=False, default=0)

    discipline_cs2: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    discipline_dota2: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    discipline_fifa: Mapped[bool] = Column(Boolean, nullable=False, default=0)

    is_registered: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    is_confirmed: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    is_banned: Mapped[bool] = Column(Boolean, nullable=False, default=0)

    tg_user: Mapped["TgUser"] = relationship("TgUser", back_populates="registration")
    team_memberships: Mapped[List["TeamMembers"]] = relationship("TeamMembers", back_populates="registration", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Registration: id={self.id}, tg_user_id={self.tg_user_id}>"


class DisciplineEnum(enum.Enum):
    CS2 = "cs2"
    DOTA2 = "dota2"
    FIFA = "fifa"


class Team(Base):
    __tablename__ = "team"

    created_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    id: Mapped[int] = Column(Integer, primary_key=True, nullable=False)
    code: Mapped[str] = Column(String(10), nullable=False, unique=True)
    title: Mapped[str] = Column(String(15), nullable=False)
    discipline: Mapped[DisciplineEnum] = Column(Enum(DisciplineEnum), nullable=False)
    owner_registration_id: Mapped[int] = Column(Integer, ForeignKey("registration.id", ondelete='CASCADE'), nullable=False)
    is_approved: Mapped[bool] = Column(Boolean, nullable=False, default=0)
    approved_datetime: Mapped[Optional[datetime.datetime]] = Column(DateTime, nullable=True)
    approved_by_admin_tg_user_id: Mapped[Optional[int]] = Column(BIGINT, ForeignKey("admin.tg_user_id", ondelete='SET NULL'))

    owner_registration: Mapped["Registration"] = relationship("Registration")
    members: Mapped[List["TeamMembers"]] = relationship("TeamMembers", back_populates="team", cascade="all, delete-orphan", viewonly=True)
    approved_by_admin: Mapped["Admin"] = relationship("Admin")

    def __repr__(self):
        return f"<Team: id={self.id}, code='{self.code}', name='{self.name}' owner_tg_user_id={self.owner_tg_user_id}, is_approved={self.is_approved}>"


class TeamMembers(Base):
    __tablename__ = "team_members"

    created_at: Mapped[datetime.datetime] = Column(DateTime, nullable=False, server_default=func.now())
    team_id: Mapped[int] = Column(Integer, ForeignKey("team.id", ondelete='CASCADE'), primary_key=True, nullable=False)
    registration_id: Mapped[int] = Column(Integer, ForeignKey("registration.id", ondelete='CASCADE'), primary_key=True, nullable=False)
    is_capitan: Mapped[bool] = Column(Boolean, nullable=False, default=0)

    team: Mapped["Team"] = relationship("Team", backref=backref("team_members", cascade="all, delete-orphan"))
    registration: Mapped["Registration"] = relationship("Registration", back_populates="team_memberships")

    def __repr__(self):
        return f"<TeamMembers: id={self.id}, team_id={self.team_id}, tg_user_id={self.tg_user_id}, is_captain={self.is_captain}>"
