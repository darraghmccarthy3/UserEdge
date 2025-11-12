import os
import sys
import uuid
from datetime import datetime, timezone
from typing import List, Optional
import bcrypt
import psycopg
from psycopg.rows import dict_row
from domain_models import User


class PostgresConnector:
    def __init__(self):
        parts = [
            f"host={os.getenv('DB_HOST', '127.0.0.1')}",
            f"port={os.getenv('DB_PORT', '5432')}",
            f"dbname={os.getenv('DB_NAME', 'projectdb')}",
            f"user={os.getenv('DB_USER', 'postuser')}",
            f"password={os.getenv('DB_PASSWORD', '')}",
        ]
        if os.getenv('DB_SSLMODE'):
            parts.append(f"sslmode={os.getenv('DB_SSLMODE', 'prefer')}")
        self.__connectString = " ".join(parts)

    def get_conn(self):
        return psycopg.connect(self.__connectString, row_factory=dict_row)

    def get_all_users(self) -> List[User]:
        """Returns list of all users from the DB."""
        q = """
        SELECT *
        FROM public.users
        ORDER BY username
        """
        with self.get_conn() as conn, conn.cursor() as cur:
            cur.execute(q)
            return [User.from_row(r) for r in cur.fetchall()]

    def create_user(self, username: str, password: str, roles: List[str]) -> uuid.UUID:
        """Creates a new user in the database."""
        now = datetime.now(timezone.utc)
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        q = """
        INSERT INTO public.users
            (username, password_hash, roles, updated_at, deleted_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """
        with self.get_conn() as conn, conn.cursor() as cur:
            cur.execute(q, (username.strip(), pw_hash, roles, now, None))
            return cur.fetchone()["id"]

    def update_user(
        self,
        user_id: str | uuid.UUID,
        username: str,
        roles: List[str],
        new_password: Optional[str],
    ) -> None:
        """Updates an existing user's info, optionally updating password."""
        if new_password:
            pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            q = """
            UPDATE public.users
            SET username=%s, roles=%s, password_hash=%s
            WHERE id=%s
            """
            params = (username.strip(), roles, pw_hash, user_id)
        else:
            q = """
            UPDATE public.users
            SET username=%s, roles=%s
            WHERE id=%s
            """
            params = (username.strip(), roles, user_id)

        with self.get_conn() as conn, conn.cursor() as cur:
            cur.execute(q, params)

    def soft_delete_user(self, user_id: str | uuid.UUID, delete: bool) -> None:
        """Soft deletes (or restores) a user by setting deleted_at."""
        deleted_at = datetime.now(timezone.utc) if delete else None
        with self.get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET deleted_at=%s WHERE id=%s",
                (deleted_at, user_id),
            )

    def hard_delete_user(self, user_id: str | uuid.UUID) -> None:
        """Permanently deletes a user from the database."""
        with self.get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM public.users WHERE id=%s", (user_id,))

#region ------ authentication methods against users_edge_pub ------
def db_health(self) -> str:
    """Short health string; useful for status badge."""
    with self.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT NOW() AS now")
        return f"DB OK · {cur.fetchone()['now']}"

def get_users_last_updated_at(self) -> Optional[datetime]:
    """Newest users.updated_at (coarse 'last sync' indicator)."""
    with self.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT MAX(updated_at) AS m FROM public.users_edge_pub")
        row = cur.fetchone()
        return row['m'] if row else None

def get_user_by_id(self, user_id: str) -> Optional[User]:
    sql = "SELECT * FROM public.users_edge_pub WHERE id = %s"
    with self.get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        return User.from_row(row) if row else None

def authenticate_user(self, username: str, password: str) -> Optional[User]:
    """Return a User if credentials are valid (and NOT soft-deleted), else None.
    NOTE: For safety, the returned User has password_hash=None.
    """
    sql = """
        SELECT id, username, password_hash, roles, updated_at, deleted_at
        FROM public.users_edge_pub
        WHERE username = %s AND deleted_at IS NULL
        LIMIT 1
    """
    with self.get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (username.strip(),))
        row = cur.fetchone()

    try:
        ok = bcrypt.checkpw(password.encode('utf-8'), row['password_hash'].encode('utf-8'))
    except Exception:
        ok = False

    if not ok:
        return None

    # Build a typed domain object and scrub the hash before returning
    user = User.from_row(row)
    user.password_hash = None
    return user
#endregion
