from datetime import datetime
import json
import sqlite3
from typing import Any, ClassVar

from utils.logger import setup_logger

logger = setup_logger()


class PersonalityManager:
    MAX_POINTS: ClassVar[int] = 10
    IMPORTANCE_ORDER: ClassVar[dict[str, int]] = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_user_personality(self, user_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT user_id, username, points, last_updated
                FROM user_personalities
                WHERE user_id = ?
            """,
                (user_id,),
            )

            row = cursor.fetchone()
            if row:
                points_json = row["points"]
                try:
                    points = json.loads(points_json) if points_json else []
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse personality points for user {user_id}")
                    points = []

                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "points": points,
                    "last_updated": row["last_updated"],
                }

            return None

    def update_user_personality(
        self,
        user_id: str,
        username: str,
        new_points: list[dict[str, str]],
    ) -> bool:
        try:
            existing_personality = self.get_user_personality(user_id)

            if existing_personality:
                existing_points = existing_personality["points"]
                merged_points = self._prioritize_points(existing_points, new_points)
            else:
                merged_points = new_points[: self.MAX_POINTS]

            points_json = json.dumps(merged_points)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO user_personalities (user_id, username, points, last_updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        points = excluded.points,
                        last_updated = excluded.last_updated
                """,
                    (user_id, username, points_json, datetime.now()),
                )
                conn.commit()

            logger.info(f"Updated personality for user {username} ({user_id}): {len(merged_points)} points")
            return True

        except Exception as e:
            logger.error(f"Failed to update personality for user {user_id}: {e}")
            return False

    def _prioritize_points(self, existing: list[dict[str, str]], new: list[dict[str, str]]) -> list[dict[str, str]]:
        all_points = []

        for point in existing:
            all_points.append(point)

        for new_point in new:
            content = new_point.get("content", "").lower().strip()
            replaced = False

            for i, existing_point in enumerate(all_points):
                existing_content = existing_point.get("content", "").lower().strip()
                if content == existing_content:
                    all_points[i] = new_point
                    replaced = True
                    break

            if not replaced:
                all_points.append(new_point)

        sorted_points = sorted(
            all_points,
            key=lambda p: (
                self.IMPORTANCE_ORDER.get(p.get("importance", "low"), 999),
                p.get("added_at", ""),
            ),
            reverse=True,
        )

        critical_points = [p for p in sorted_points if p.get("importance") == "critical"]
        non_critical_points = [p for p in sorted_points if p.get("importance") != "critical"]

        if len(critical_points) >= self.MAX_POINTS:
            logger.warning(f"User has {len(critical_points)} critical points, keeping only first {self.MAX_POINTS}")
            return critical_points[: self.MAX_POINTS]

        remaining_slots = self.MAX_POINTS - len(critical_points)
        return critical_points + non_critical_points[:remaining_slots]

    def format_personality_for_prompt(self, personality: dict[str, Any] | None) -> str:
        if not personality or not personality.get("points"):
            return ""

        points = personality["points"]
        lines = [f"\nUser Personality ({len(points)}/{self.MAX_POINTS} points):"]

        for i, point in enumerate(points, 1):
            importance = point.get("importance", "unknown")
            content = point.get("content", "")
            lines.append(f"{i}. [{importance}] {content}")

        return "\n".join(lines)
