from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.conversations import owned_conversation
from app.api.deps import admin_user, current_user
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_conversation_lookup_is_scoped_to_the_authenticated_user():
    user_id, conversation_id = uuid4(), uuid4()
    db = SimpleNamespace(scalar=AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as error:
        await owned_conversation(db, SimpleNamespace(id=user_id), conversation_id)
    assert error.value.status_code == 404
    statement = db.scalar.await_args.args[0]
    criteria = statement.whereclause.compile().params
    assert str(user_id) in {str(value) for value in criteria.values()}
    assert str(conversation_id) in {str(value) for value in criteria.values()}


@pytest.mark.asyncio
async def test_bearer_token_resolves_active_user():
    user_id = uuid4()
    user = SimpleNamespace(id=user_id, is_active=True)
    db = SimpleNamespace(scalar=AsyncMock(return_value=user))
    credentials = SimpleNamespace(credentials=create_access_token(str(user_id)))
    assert await current_user(credentials, db) is user


@pytest.mark.asyncio
async def test_admin_gate_rejects_member():
    with pytest.raises(HTTPException) as error:
        await admin_user(SimpleNamespace(is_admin=False))
    assert error.value.status_code == 403
