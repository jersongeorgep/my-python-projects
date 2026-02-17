# lib/gantt.py
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd


def create_gantt_chart(tasks_df: pd.DataFrame) -> BytesIO | None:
    if tasks_df is None or tasks_df.empty:
        return None

    df = tasks_df.copy()
    required_cols = {"Task", "Start", "End"}
    if not required_cols.issubset(df.columns):
        return None

    df["Start"] = pd.to_datetime(df["Start"], errors="coerce")
    df["End"] = pd.to_datetime(df["End"], errors="coerce")
    df = df.dropna(subset=["Start", "End", "Task"])

    if df.empty:
        return None

    df = df.sort_values("Start")

    fig, ax = plt.subplots(figsize=(8, 4))
    for _, row in df.iterrows():
        duration = (row["End"] - row["Start"]).days
        if duration <= 0:
            duration = 1
        ax.barh(row["Task"], duration, left=row["Start"])

    ax.set_xlabel("Date")
    ax.set_ylabel("Task")
    ax.set_title("Project Gantt Chart")
    fig.autofmt_xdate()

    img = BytesIO()
    fig.savefig(img, format="png", bbox_inches="tight")
    img.seek(0)
    plt.close(fig)
    return img
