# lib/db.py
import pandas as pd
from sqlalchemy import create_engine, text

import pymysql  # noqa: F401  (needed for mysql+pymysql)

# ===================== DB CONFIG =====================

ENGINE = create_engine(
    "mysql+pymysql://root:@localhost/iso_data?charset=utf8mb4",
    echo=False,
    future=True,
)

# ===================== DB HELPERS =====================


def db_get_projects_list():
    query = "SELECT id, name FROM projects ORDER BY id DESC"
    with ENGINE.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def db_get_project(project_id: int):
    query = "SELECT * FROM projects WHERE id = :id"
    with ENGINE.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"id": project_id})
    return df.to_dict(orient="records")[0] if not df.empty else None


def db_get_df(table: str, project_id: int) -> pd.DataFrame:
    query = f"SELECT * FROM {table} WHERE project_id = :pid"
    with ENGINE.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"pid": project_id})
    return df


def db_save_df(table: str, project_id: int, df: pd.DataFrame, id_col: str = "id"):
    """
    Delete all old rows for project_id, then insert current df.
    """
    with ENGINE.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE project_id = :pid"), {"pid": project_id})
        if not df.empty:
            df = df.copy()
            df["project_id"] = project_id
            if id_col in df.columns:
                df = df.drop(columns=[id_col])
            df.to_sql(table, conn, if_exists="append", index=False)


def db_get_section(project_id: int, key: str) -> str:
    if project_id is None:
        return ""
    query = """
        SELECT content FROM project_sections
        WHERE project_id = :pid AND section_key = :key
        LIMIT 1
    """
    with ENGINE.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"pid": project_id, "key": key})
    return df["content"].iloc[0] if not df.empty else ""


def db_save_section(project_id: int, key: str, content: str):
    query = """
        INSERT INTO project_sections (project_id, section_key, content)
        VALUES (:pid, :key, :content)
        ON DUPLICATE KEY UPDATE content = VALUES(content)
    """
    with ENGINE.begin() as conn:
        conn.execute(text(query), {"pid": project_id, "key": key, "content": content})


def upsert_project(
    project_name,
    client_name,
    project_code,
    start_date,
    end_date,
    overview,
    scope_in_scope,
    scope_out_scope,
):
    """
    If a project with same name or code exists, delete it and children,
    then insert a fresh one. Return new_id.
    """
    with ENGINE.begin() as conn:
        existing = conn.execute(
            """
            SELECT id FROM projects
            WHERE name = %s OR project_code = %s
            LIMIT 1
            """,
            (project_name, project_code),
        ).fetchone()

        if existing:
            old_id = existing[0]
            # delete children first
            conn.execute("DELETE FROM project_team_members WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM project_tasks WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM project_risks WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM project_test_cases WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM project_apis WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM project_change_requests WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM project_sections WHERE project_id=%s", (old_id,))
            conn.execute("DELETE FROM projects WHERE id=%s", (old_id,))

        result = conn.execute(
            """
            INSERT INTO projects
            (name, client_name, project_code, start_date, end_date,
             overview, scope_in_scope, scope_out_scope)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                project_name,
                client_name,
                project_code,
                start_date,
                end_date,
                overview,
                scope_in_scope,
                scope_out_scope,
            ),
        )
        return result.lastrowid
