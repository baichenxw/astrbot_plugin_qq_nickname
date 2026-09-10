"""Persistent profiles keyed by the original bot ID and OpenID."""

import re
import sqlite3
import unicodedata
from pathlib import Path


class ConflictError(ValueError):
    """The profile changed since the administrator opened the editor."""


class ProfileStore:
    """Store presentation fields without changing platform identity."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS profiles (
                bot_id TEXT NOT NULL, openid TEXT NOT NULL,
                nickname TEXT NOT NULL DEFAULT '', qq TEXT NOT NULL DEFAULT '',
                revision INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (bot_id, openid))""")
            db.execute("""CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value INTEGER NOT NULL CHECK(value IN (0,1)))""")
        path.chmod(0o600)

    def backend_only(self) -> bool:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT value FROM settings WHERE key='backend_only'"
            ).fetchone()
            return bool(row[0]) if row else False

    def set_backend_only(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("仅允许后台管理资料必须为布尔值")
        with sqlite3.connect(self.path) as db:
            db.execute(
                """INSERT INTO settings(key,value) VALUES('backend_only',?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (int(enabled),),
            )

    def get(self, bot_id: str, openid: str) -> dict | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM profiles WHERE bot_id=? AND openid=?", (bot_id, openid)
            ).fetchone()
            return dict(row) if row else None

    def save(self, bot_id: str, openid: str, patch: dict, revision=None) -> dict:
        """Atomically merge fields and optionally reject a stale edit.

        Args:
            bot_id: Existing AstrBot platform instance ID.
            openid: Original user identifier received from QQ.
            patch: Nickname and/or QQ fields to update; empty clears a field.
            revision: Expected revision, or zero for a new profile.

        Returns:
            The saved profile.
        """
        if not isinstance(bot_id, str) or not re.fullmatch(r"[\w.-]{1,80}", bot_id):
            raise ValueError("机器人 ID 格式不正确")
        if not isinstance(openid, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", openid
        ):
            raise ValueError("请填写原始 OpenID，不能填写完整 UMO")
        if not patch or set(patch) - {"nickname", "qq"}:
            raise ValueError("只能修改昵称和 QQ 号")
        values = {}
        for key, value in patch.items():
            if not isinstance(value, str):
                # Keep user-input errors consistent with the API's ValueError handler.
                raise ValueError("昵称和 QQ 号必须是文本")  # noqa: TRY004
            value = value.strip()
            if key == "nickname":
                if len(value) > 32 or any(
                    unicodedata.category(c).startswith("C") or c in '<>[]{}\\"'
                    for c in value
                ):
                    raise ValueError(
                        "昵称最多 32 个字符，不能含控制字符、换行、双引号或括号标记"
                    )
            elif value and not re.fullmatch(r"[1-9][0-9]{4,11}", value):
                raise ValueError("QQ 号应为 5–12 位数字，不能以 0 开头")
            values[key] = value
        with sqlite3.connect(self.path, timeout=5) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM profiles WHERE bot_id=? AND openid=?", (bot_id, openid)
            ).fetchone()
            current = dict(row) if row else {"nickname": "", "qq": "", "revision": 0}
            if revision is not None and revision != current["revision"]:
                raise ConflictError("资料已被修改，请刷新列表后重新编辑")
            current.update(values)
            db.execute(
                """INSERT INTO profiles(bot_id,openid,nickname,qq,revision)
                VALUES(?,?,?,?,?) ON CONFLICT(bot_id,openid) DO UPDATE SET
                nickname=excluded.nickname, qq=excluded.qq, revision=excluded.revision,
                updated_at=CURRENT_TIMESTAMP""",
                (
                    bot_id,
                    openid,
                    current["nickname"],
                    current["qq"],
                    current["revision"] + 1,
                ),
            )
        return self.get(bot_id, openid)

    def list(self, query: str = "", offset: int = 0, limit: int = 100) -> dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            pattern = (
                "%"
                + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                + "%"
            )
            where = "WHERE (bot_id || ' ' || openid || ' ' || nickname || ' ' || qq) LIKE ? ESCAPE '\\'"
            total = db.execute(
                "SELECT COUNT(*) FROM profiles " + where, (pattern,)
            ).fetchone()[0]
            rows = db.execute(
                "SELECT * FROM profiles "
                + where
                + " ORDER BY updated_at DESC,bot_id,openid LIMIT ? OFFSET ?",
                (pattern, min(max(limit, 1), 100), max(offset, 0)),
            ).fetchall()
            return {"records": [dict(row) for row in rows], "total": total}

    def delete(self, bot_id: str, openid: str, revision: int) -> bool:
        if (
            not isinstance(bot_id, str)
            or not isinstance(openid, str)
            or type(revision) is not int
        ):
            raise ValueError("请求格式不正确")
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "DELETE FROM profiles WHERE bot_id=? AND openid=? AND revision=?",
                (bot_id, openid, revision),
            )
            if not cursor.rowcount:
                raise ConflictError("资料已改变或被删除，请刷新后重试")
        return True
