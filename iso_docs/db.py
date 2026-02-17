from sqlalchemy import create_engine
import pandas as pd

# adjust host/user/pass/db
engine = create_engine("mysql+pymysql://user:password@localhost/iso_db", echo=False)

def get_projects_list():
    return pd.read_sql("SELECT id, name FROM projects ORDER BY id DESC", engine)

def get_project(project_id: int):
    project = pd.read_sql(
        "SELECT * FROM projects WHERE id = %s", engine, params=[project_id]
    ).to_dict(orient="records")
    return project[0] if project else None

def get_df(table, project_id):
    return pd.read_sql(
        f"SELECT * FROM {table} WHERE project_id = %s",
        engine,
        params=[project_id],
    )

def save_df(table, project_id, df, id_column="id"):
    # simple strategy: delete + insert (easier for now)
    with engine.begin() as conn:
        conn.execute(f"DELETE FROM {table} WHERE project_id = %s", (project_id,))
        if not df.empty:
            df = df.copy()
            df["project_id"] = project_id
            # remove id column if present
            if id_column in df.columns:
                df = df.drop(columns=[id_column])
            df.to_sql(table, conn, if_exists="append", index=False)

def get_section(project_id, key):
    df = pd.read_sql(
        "SELECT content FROM project_sections WHERE project_id=%s AND section_key=%s",
        engine,
        params=[project_id, key],
    )
    return df["content"].iloc[0] if not df.empty else ""

def save_section(project_id, key, content):
    with engine.begin() as conn:
        conn.execute(
            """
            INSERT INTO project_sections (project_id, section_key, content)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE content = VALUES(content)
            """,
            (project_id, key, content),
        )



