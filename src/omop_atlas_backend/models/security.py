# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

"""
Phase 1: Security Core - Models
Defines the User, Role, and Permission models for RBAC.
"""

from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omop_atlas_backend.models.base import Base

# Association Tables
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class Permission(Base):
    """
    Security Permission.
    Represents a granular access right (e.g., 'concept_set:create').
    """

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, value='{self.value}')>"


class Role(Base):
    """
    Security Role.
    A collection of permissions assigned to users.
    """

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    permissions: Mapped[List[Permission]] = relationship(secondary=role_permissions, lazy="selectin")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"


class User(Base):
    """
    Security User.
    The principal entity for authentication and authorization.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    roles: Mapped[List[Role]] = relationship(secondary=user_roles, lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
