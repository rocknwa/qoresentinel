"""Simple local SQLite metadata and source storage for the Phase 1 prototype."""
import json
import sqlite3
import uuid
from pathlib import Path
from .settings import DATA_DIR

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA_DIR / "qoresentinel.sqlite", timeout=10)
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, files TEXT NOT NULL DEFAULT '{}')")
    return db

def create_project(name: str):
    project_id = str(uuid.uuid4())
    with connect() as db:
        db.execute("INSERT INTO projects(id,name) VALUES (?,?)", (project_id, name))
    return {"id": project_id, "name": name, "file_count": 0}

def get_project(project_id: str):
    with connect() as db:
        row = db.execute("SELECT id,name,files FROM projects WHERE id=?", (project_id,)).fetchone()
    return row

def save_files(project_id: str, files: dict[str,str]):
    with connect() as db:
        row=db.execute("SELECT files FROM projects WHERE id=?",(project_id,)).fetchone()
        if row is None: return None
        current=json.loads(row[0]); current.update(files)
        db.execute("UPDATE projects SET files=? WHERE id=?",(json.dumps(current),project_id))
        return sorted(current)
