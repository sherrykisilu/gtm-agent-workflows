import asyncio
import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from app.models import (
    AccountBrief,
    PolicyResult,
    WorkflowCreate,
    WorkflowEvent,
    WorkflowRecord,
    WorkflowState,
)

T = TypeVar("T")


class WorkflowStore:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        def create() -> None:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS workflows (
                        id TEXT PRIMARY KEY,
                        idempotency_key TEXT NOT NULL UNIQUE,
                        state TEXT NOT NULL,
                        request_json TEXT NOT NULL,
                        result_json TEXT,
                        policy_json TEXT,
                        error TEXT,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS workflow_events (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        workflow_id TEXT NOT NULL,
                        state TEXT NOT NULL,
                        detail TEXT NOT NULL,
                        at TEXT NOT NULL,
                        FOREIGN KEY(workflow_id) REFERENCES workflows(id)
                    );
                    """
                )

        await asyncio.to_thread(create)

    async def _write(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        async with self._write_lock:
            def execute() -> T:
                with self._connect() as connection:
                    result = operation(connection)
                    connection.commit()
                    return result

            return await asyncio.to_thread(execute)

    async def create(
        self, workflow_id: str, idempotency_key: str, request: WorkflowCreate
    ) -> WorkflowRecord:
        now = datetime.now(UTC)

        def insert(connection: sqlite3.Connection) -> None:
            connection.execute(
                """
                INSERT INTO workflows (
                    id, idempotency_key, state, request_json, attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    workflow_id,
                    idempotency_key,
                    WorkflowState.RECEIVED,
                    request.model_dump_json(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO workflow_events (workflow_id, state, detail, at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    WorkflowState.RECEIVED,
                    "Request accepted and durably recorded",
                    now.isoformat(),
                ),
            )

        await self._write(insert)
        record = await self.get(workflow_id)
        if record is None:
            raise RuntimeError("workflow disappeared after creation")
        return record

    async def get_by_idempotency_key(self, key: str) -> WorkflowRecord | None:
        return await self._fetch_one("idempotency_key", key)

    async def get(self, workflow_id: str) -> WorkflowRecord | None:
        return await self._fetch_one("id", workflow_id)

    async def _fetch_one(self, column: str, value: str) -> WorkflowRecord | None:
        if column not in {"id", "idempotency_key"}:
            raise ValueError("unsupported lookup column")

        def query() -> WorkflowRecord | None:
            with self._connect() as connection:
                row = connection.execute(
                    f"SELECT * FROM workflows WHERE {column} = ?", (value,)
                ).fetchone()
                if row is None:
                    return None
                return self._to_record(connection, row)

        return await asyncio.to_thread(query)

    async def list(self) -> list[WorkflowRecord]:
        def query() -> list[WorkflowRecord]:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM workflows ORDER BY created_at DESC"
                ).fetchall()
                return [self._to_record(connection, row) for row in rows]

        return await asyncio.to_thread(query)

    async def transition(
        self,
        workflow_id: str,
        state: WorkflowState,
        detail: str,
        *,
        result: AccountBrief | None = None,
        policy: PolicyResult | None = None,
        error: str | None = None,
        increment_attempts: bool = False,
    ) -> WorkflowRecord:
        now = datetime.now(UTC)

        def update(connection: sqlite3.Connection) -> None:
            current = connection.execute(
                "SELECT attempts FROM workflows WHERE id = ?", (workflow_id,)
            ).fetchone()
            if current is None:
                raise KeyError(workflow_id)
            attempts = current["attempts"] + (1 if increment_attempts else 0)
            connection.execute(
                """
                UPDATE workflows
                SET state = ?, result_json = COALESCE(?, result_json),
                    policy_json = COALESCE(?, policy_json), error = ?,
                    attempts = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    state,
                    result.model_dump_json() if result else None,
                    policy.model_dump_json() if policy else None,
                    error,
                    attempts,
                    now.isoformat(),
                    workflow_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO workflow_events (workflow_id, state, detail, at)
                VALUES (?, ?, ?, ?)
                """,
                (workflow_id, state, detail, now.isoformat()),
            )

        await self._write(update)
        record = await self.get(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        return record

    def _to_record(
        self, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> WorkflowRecord:
        event_rows = connection.execute(
            """
            SELECT state, detail, at FROM workflow_events
            WHERE workflow_id = ? ORDER BY sequence
            """,
            (row["id"],),
        ).fetchall()
        return WorkflowRecord(
            id=row["id"],
            idempotency_key=row["idempotency_key"],
            state=WorkflowState(row["state"]),
            request=WorkflowCreate.model_validate_json(row["request_json"]),
            result=AccountBrief.model_validate_json(row["result_json"])
            if row["result_json"]
            else None,
            policy=PolicyResult.model_validate_json(row["policy_json"])
            if row["policy_json"]
            else None,
            error=row["error"],
            attempts=row["attempts"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            events=[
                WorkflowEvent(
                    state=WorkflowState(event["state"]),
                    detail=event["detail"],
                    at=datetime.fromisoformat(event["at"]),
                )
                for event in event_rows
            ],
        )

    async def reset(self) -> None:
        def delete(connection: sqlite3.Connection) -> None:
            connection.execute("DELETE FROM workflow_events")
            connection.execute("DELETE FROM workflows")

        await self._write(delete)

