"""认证服务的单元测试。"""

from datetime import datetime, timedelta

import pytest

from app.repositories.mysql.records import AuthSessionRecord, UserRecord
from app.services.auth_service import AuthService, hash_password


class FakeAuthRepository:
    """内存实现的认证仓储，覆盖 AuthService 用到的方法。"""

    def __init__(self) -> None:
        self.users: dict[int, UserRecord] = {}
        self.users_by_name: dict[str, UserRecord] = {}
        self.sessions: dict[str, AuthSessionRecord] = {}
        self._next_id = 1

    def add_user(self, username: str, password: str, status: int = 1) -> UserRecord:
        salt = "salt"
        user = UserRecord(
            id=self._next_id,
            username=username,
            password_hash=hash_password(password, salt),
            salt=salt,
            nickname=username,
            avatar=None,
            status=status,
        )
        self.users[user.id] = user
        self.users_by_name[username] = user
        self._next_id += 1
        return user

    def get_user_by_username(self, username: str) -> UserRecord | None:
        return self.users_by_name.get(username)

    def get_user_by_id(self, user_id: int) -> UserRecord | None:
        return self.users.get(user_id)

    def create_auth_session(self, user_id: int, token: str, ttl_minutes: int) -> AuthSessionRecord:
        record = AuthSessionRecord(
            id=len(self.sessions) + 1,
            user_id=user_id,
            token=token,
            expires_at=datetime(2026, 1, 1) + timedelta(minutes=ttl_minutes),
        )
        self.sessions[token] = record
        return record

    def get_auth_session(self, token: str) -> AuthSessionRecord | None:
        return self.sessions.get(token)

    def revoke_auth_session(self, token: str) -> None:
        self.sessions.pop(token, None)


def _service() -> tuple[AuthService, FakeAuthRepository]:
    repo = FakeAuthRepository()
    return AuthService(repo, session_ttl_minutes=60), repo  # type: ignore[arg-type]


def test_login_success_returns_token_and_user() -> None:
    service, repo = _service()
    repo.add_user("alice", "secret")
    result = service.login("alice", "secret")
    assert result.user.username == "alice"
    assert repo.get_auth_session(result.token) is not None


def test_login_wrong_password_raises() -> None:
    service, repo = _service()
    repo.add_user("alice", "secret")
    with pytest.raises(ValueError):
        service.login("alice", "wrong")


def test_login_disabled_user_raises() -> None:
    service, repo = _service()
    repo.add_user("bob", "secret", status=0)
    with pytest.raises(ValueError):
        service.login("bob", "secret")


def test_authenticate_token_valid() -> None:
    service, repo = _service()
    user = repo.add_user("alice", "secret")
    result = service.login("alice", "secret")
    authenticated = service.authenticate_token(result.token)
    assert authenticated is not None
    assert authenticated.id == user.id


def test_authenticate_token_unknown_returns_none() -> None:
    service, _ = _service()
    assert service.authenticate_token("does-not-exist") is None


def test_register_rejects_duplicate_username() -> None:
    service, repo = _service()
    repo.add_user("alice", "secret")
    with pytest.raises(ValueError):
        service.register("alice", "secret", "secret")


def test_register_rejects_mismatched_confirm() -> None:
    service, _ = _service()
    with pytest.raises(ValueError):
        service.register("newuser", "secret", "different")


def test_logout_revokes_session() -> None:
    service, repo = _service()
    repo.add_user("alice", "secret")
    result = service.login("alice", "secret")
    service.logout(result.token)
    assert service.authenticate_token(result.token) is None
