# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/omop_atlas_backend

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omop_atlas_backend.models.security import Permission, Role, User


@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession) -> None:
    """Test creating a new user."""
    user = User(username="testuser", password_hash="hashed_secret")
    async_session.add(user)
    await async_session.commit()

    stmt = select(User).where(User.username == "testuser")
    result = await async_session.execute(stmt)
    retrieved_user = result.scalar_one()

    assert retrieved_user.username == "testuser"
    assert retrieved_user.password_hash == "hashed_secret"
    assert retrieved_user.is_active is True
    assert retrieved_user.is_superuser is False
    assert repr(retrieved_user) == "<User(id=1, username='testuser')>"


@pytest.mark.asyncio
async def test_rbac_relationships(async_session: AsyncSession) -> None:
    """Test User-Role and Role-Permission relationships."""
    # Create Permissions
    perm1 = Permission(value="vocab:read", description="Read Vocabulary")
    perm2 = Permission(value="cohort:write", description="Write Cohorts")
    async_session.add_all([perm1, perm2])

    # Create Roles
    admin_role = Role(name="admin")
    user_role = Role(name="user")

    # Verify Repr
    assert repr(perm1) == "<Permission(id=None, value='vocab:read')>"
    assert repr(admin_role) == "<Role(id=None, name='admin')>"

    # Assign permissions
    admin_role.permissions.extend([perm1, perm2])
    user_role.permissions.append(perm1)

    async_session.add_all([admin_role, user_role])

    # Create User
    alice = User(username="alice", password_hash="secret")
    alice.roles.append(admin_role)

    bob = User(username="bob", password_hash="secret")
    bob.roles.append(user_role)

    async_session.add_all([alice, bob])
    await async_session.commit()

    # Re-fetch alice with eager loading
    stmt = select(User).where(User.username == "alice")
    result = await async_session.execute(stmt)
    alice = result.scalar_one()

    assert len(alice.roles) == 1
    assert alice.roles[0].name == "admin"
    assert len(alice.roles[0].permissions) == 2
    perm_values = {p.value for p in alice.roles[0].permissions}
    assert "vocab:read" in perm_values
    assert "cohort:write" in perm_values

    # Re-fetch bob
    stmt = select(User).where(User.username == "bob")
    result = await async_session.execute(stmt)
    bob = result.scalar_one()

    assert len(bob.roles) == 1
    assert bob.roles[0].name == "user"
    assert len(bob.roles[0].permissions) == 1
    assert bob.roles[0].permissions[0].value == "vocab:read"
