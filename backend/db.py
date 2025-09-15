import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class SessionStore:
    """SQLite-backed store for session data as JSON blobs."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create(self, initial_data: Optional[Dict[str, Any]] = None) -> str:
        session_id = initial_data.get("session_id") if initial_data else None
        if not session_id:
            # Do not import uuid here to keep this module self-contained
            # The caller should set session_id when needed; but generate if not provided
            import uuid
            session_id = str(uuid.uuid4())

        now = datetime.now().isoformat()
        data = initial_data or {}
        data["session_id"] = session_id

        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, data, created_at, last_activity) VALUES (?, ?, ?, ?)",
                (session_id, json.dumps(data), now, now),
            )
            conn.commit()
        return session_id

    def get(self, session_id: str) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT data FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            try:
                return json.loads(row["data"]) or {}
            except Exception:
                return {}

    def exists(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            return cur.fetchone() is not None

    def update(self, session_id: str, data_updates: Dict[str, Any]) -> bool:
        current = self.get(session_id)
        if not current:
            return False
        current.update(data_updates)
        current["last_activity"] = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET data = ?, last_activity = ? WHERE session_id = ?",
                (json.dumps(current), current["last_activity"], session_id),
            )
            conn.commit()
        return True

    def delete(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_all(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT data FROM sessions")
            rows = cur.fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                try:
                    results.append(json.loads(row["data"]))
                except Exception:
                    continue
            return results

    def prune_inactive_before(self, cutoff_iso: str) -> List[str]:
        """Delete sessions with last_activity earlier than cutoff. Returns deleted ids."""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT session_id, last_activity FROM sessions WHERE last_activity < ?",
                (cutoff_iso,),
            )
            ids = [r["session_id"] for r in cur.fetchall()]
            if ids:
                conn.executemany(
                    "DELETE FROM sessions WHERE session_id = ?",
                    [(sid,) for sid in ids],
                )
                conn.commit()
            return ids

