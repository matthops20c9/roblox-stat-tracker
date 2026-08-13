import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class TrackerDB:
    """Handles local SQLite storage for place-to-universe resolution and history."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mappings (
                    place_id INTEGER PRIMARY KEY,
                    universe_id INTEGER NOT NULL,
                    mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS universes (
                    universe_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    creator_name TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    universe_id INTEGER,
                    timestamp TEXT NOT NULL,
                    active_players INTEGER,
                    visits INTEGER,
                    favorites INTEGER,
                    upvotes INTEGER,
                    downvotes INTEGER,
                    PRIMARY KEY (universe_id, timestamp)
                )
            """)
            # Index to accelerate history range scans
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_lookup 
                ON snapshots (universe_id, timestamp DESC)
            """)
            conn.commit()

    def get_universe_id(self, place_id: int) -> int | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT universe_id FROM mappings WHERE place_id = ?",
                (place_id,)
            ).fetchone()
            return row[0] if row else None

    def set_universe_id(self, place_id: int, universe_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mappings (place_id, universe_id) VALUES (?, ?)",
                (place_id, universe_id)
            )
            conn.commit()

    def record_snapshot(self, universe_id: int, name: str, creator: str, active: int, visits: int, favorites: int, upvotes: int, downvotes: int):
        now = datetime.now().isoformat()
        # print(f"DEBUG DB: recording {universe_id} ({name}) -> active={active} visits={visits}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO universes (universe_id, name, creator_name) VALUES (?, ?, ?)",
                (universe_id, name, creator)
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (universe_id, timestamp, active_players, visits, favorites, upvotes, downvotes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (universe_id, now, active, visits, favorites, upvotes, downvotes)
            )
            conn.commit()

    def get_tracked_games(self) -> list[dict]:
        query = """
            SELECT 
                u.universe_id, 
                u.name, 
                u.creator_name,
                s.timestamp, 
                s.active_players, 
                s.visits, 
                s.favorites, 
                s.upvotes, 
                s.downvotes,
                m.place_id
            FROM universes u
            JOIN snapshots s ON s.universe_id = u.universe_id
            LEFT JOIN mappings m ON m.universe_id = u.universe_id
            WHERE s.timestamp = (
                SELECT MAX(timestamp) 
                FROM snapshots 
                WHERE snapshots.universe_id = u.universe_id
            )
            ORDER BY s.active_players DESC
        """
        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query).fetchall():
                results.append(dict(row))
        return results

    def get_history(self, universe_id: int, days: int = 7) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query = """
            SELECT timestamp, active_players, visits, favorites, upvotes, downvotes
            FROM snapshots
            WHERE universe_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """
        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, (universe_id, cutoff)).fetchall():
                results.append(dict(row))
        return results

    def prune_snapshots(self, keep_days: int):
        # Keep DB slim by cutting off snapshots older than keep_days
        univ_id = keep_days
        cutoff = (datetime.now() - timedelta(days=univ_id)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM snapshots WHERE timestamp < ?",
                (cutoff,)
            )
            conn.commit()
