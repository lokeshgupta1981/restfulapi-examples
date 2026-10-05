"""MCP server for a small project task tracker backed by SQLite.

Run over stdio (default):            python server.py
Run over Streamable HTTP on :8040:   python server.py --http
"""

import json
import logging
import sys
from datetime import date
from typing import Annotated, Literal

import anyio
from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations

import db

# stdout belongs to the protocol on stdio, so every log line goes to stderr.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("task-tracker")

mcp = MCPServer(
    "task-tracker",
    version="1.0.0",
    instructions="Task tracker for small software projects. "
    "Project keys are short uppercase codes such as APP or WEB.",
)

Status = Literal["todo", "in_progress", "done"]


class Task(BaseModel):
    id: int
    project: str
    title: str
    status: Status
    assignee: str | None
    due_date: date | None


class ProjectReport(BaseModel):
    project: str
    total: int
    by_status: dict[str, int]
    overdue: list[Task]


def require_project(conn, project: str) -> None:
    """Raise a ToolError the model can act on when the project key is unknown."""
    row = conn.execute("SELECT 1 FROM projects WHERE key = ?", (project,)).fetchone()
    if row is None:
        keys = [r["key"] for r in conn.execute("SELECT key FROM projects ORDER BY key")]
        raise ToolError(f"Unknown project '{project}'. Known project keys: {', '.join(keys)}.")


# ---------- Tools ----------

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def search_tasks(
    project: Annotated[str, Field(description="Project key, for example APP")],
    status: Status | None = None,
    assignee: Annotated[str | None, Field(description="Username, for example maria")] = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
) -> list[Task]:
    """Find tasks in one project. Filter by status and assignee.
    Results are ordered by due date, tasks without a due date last."""
    sql = "SELECT * FROM tasks WHERE project = ?"
    params: list = [project]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if assignee:
        sql += " AND assignee = ?"
        params.append(assignee)
    sql += " ORDER BY due_date IS NULL, due_date, id LIMIT ?"
    params.append(limit)
    with db.connect() as conn:
        require_project(conn, project)
        rows = conn.execute(sql, params).fetchall()
    log.info("search_tasks project=%s status=%s -> %d rows", project, status, len(rows))
    return [Task(**dict(row)) for row in rows]


@mcp.tool()
def create_task(
    project: Annotated[str, Field(description="Project key, for example APP")],
    title: Annotated[str, Field(min_length=3, max_length=200)],
    assignee: str | None = None,
    due_date: date | None = None,
) -> Task:
    """Create a task with status todo and return it."""
    with db.connect() as conn:
        require_project(conn, project)
        cursor = conn.execute(
            "INSERT INTO tasks (project, title, status, assignee, due_date) VALUES (?, ?, 'todo', ?, ?)",
            (project, title, assignee, due_date.isoformat() if due_date else None),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    log.info("create_task id=%d project=%s", row["id"], project)
    return Task(**dict(row))


@mcp.tool(annotations=ToolAnnotations(idempotentHint=True))
def complete_task(task_id: int) -> Task:
    """Mark a task as done. Fails if the task does not exist or is already done."""
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ToolError(f"Task {task_id} does not exist. Use search_tasks to find task IDs.")
        if row["status"] == "done":
            raise ToolError(f"Task {task_id} is already done. No change was made.")
        conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    log.info("complete_task id=%d", task_id)
    return Task(**dict(row))


def _count_by_status(project: str) -> dict[str, int]:
    with db.connect() as conn:
        require_project(conn, project)
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM tasks WHERE project = ? GROUP BY status ORDER BY status",
            (project,),
        ).fetchall()
    return {row["status"]: row["n"] for row in rows}


def _overdue(project: str, today: str) -> list[Task]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project = ? AND status != 'done' AND due_date < ? ORDER BY due_date",
            (project, today),
        ).fetchall()
    return [Task(**dict(row)) for row in rows]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def project_report(
    project: str,
    ctx: Context,
    today: Annotated[date | None, Field(description="Report date, defaults to today")] = None,
) -> ProjectReport:
    """Summarize one project: task counts per status and the overdue open tasks."""
    report_date = (today or date.today()).isoformat()
    await ctx.report_progress(0, 2, "Counting tasks")
    # sqlite3 blocks, so run it in a worker thread and keep the event loop free.
    by_status = await anyio.to_thread.run_sync(_count_by_status, project)
    await ctx.report_progress(1, 2, "Finding overdue tasks")
    overdue = await anyio.to_thread.run_sync(_overdue, project, report_date)
    await ctx.report_progress(2, 2, "Done")
    return ProjectReport(
        project=project, total=sum(by_status.values()), by_status=by_status, overdue=overdue
    )


# ---------- Resources ----------

@mcp.resource("tasks://projects", mime_type="application/json")
def list_projects() -> str:
    """All projects with their key, name and owner."""
    with db.connect() as conn:
        rows = conn.execute("SELECT key, name, owner FROM projects ORDER BY key").fetchall()
    return json.dumps([dict(row) for row in rows])


@mcp.resource("tasks://projects/{key}/summary", mime_type="text/markdown")
def project_summary(key: str) -> str:
    """A short Markdown summary of one project's open tasks."""
    with db.connect() as conn:
        project = conn.execute("SELECT * FROM projects WHERE key = ?", (key,)).fetchone()
        if project is None:
            raise ResourceNotFoundError(f"No project with key '{key}'")
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project = ? AND status != 'done' ORDER BY due_date IS NULL, due_date",
            (key,),
        ).fetchall()
    lines = [f"# {project['name']} ({key})", f"Owner: {project['owner']}", ""]
    for row in rows:
        due = row["due_date"] or "no due date"
        lines.append(f"- #{row['id']} {row['title']} [{row['status']}] {row['assignee'] or 'unassigned'}, due {due}")
    return "\n".join(lines)


# ---------- Prompts ----------

@mcp.prompt(title="Weekly status update")
def weekly_update(project: str) -> str:
    """Draft a weekly status update for one project."""
    return (
        f"Write a short weekly status update for project {project}. "
        f"Call project_report for {project} first, then search_tasks with status in_progress. "
        "List finished work, work in progress and overdue tasks with their owners. "
        "Keep it under 150 words."
    )


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run("streamable-http", host="127.0.0.1", port=8040)
    else:
        mcp.run()
