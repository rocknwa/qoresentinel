from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from .ingestion import BadSource, ingest_files, ingest_paste, ingest_zip, as_http_error
from .storage import create_project, get_project, save_files
from .audit_service import analyze, EngineNotConfigured
import json

app = FastAPI(title="QoreSentinel API", version="0.1.0")

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

class PasteInput(BaseModel):
    source: str = Field(min_length=1)

@app.get("/health")
def health():
    return {"status":"ok", "service":"qoresentinel-backend"}

@app.post("/api/v1/projects", status_code=201)
def new_project(payload: ProjectCreate):
    return create_project(payload.name)

@app.get("/api/v1/projects/{project_id}")
def project(project_id: str):
    row = get_project(project_id)
    if row is None: raise HTTPException(404, "Project not found")
    return {"id":row[0],"name":row[1],"files":sorted(json.loads(row[2]))}

@app.post("/api/v1/projects/{project_id}/source")
def paste(project_id: str, payload: PasteInput):
    if get_project(project_id) is None: raise HTTPException(404,"Project not found")
    try: files = ingest_paste(payload.source)
    except BadSource as exc: raise as_http_error(exc) from exc
    return {"files":save_files(project_id,files)}

@app.post("/api/v1/projects/{project_id}/files")
async def upload(project_id: str, files: list[UploadFile] = File(...)):
    if get_project(project_id) is None: raise HTTPException(404,"Project not found")
    if len(files) != 1 and any((f.filename or "").lower().endswith(".zip") for f in files):
        raise HTTPException(422,"Submit ZIP by itself")
    if len(files)>80: raise HTTPException(422,"Too many files")
    try:
        items=[]
        for f in files:
            data=await f.read(4_000_001)
            if len(data)>4_000_000: raise BadSource("Upload exceeds size limit")
            items.append((f.filename or "",data))
        if len(items)==1 and items[0][0].lower().endswith(".zip"):
            sources=ingest_zip(items[0][1])
        else:
            sources=ingest_files(items)
    except BadSource as exc: raise as_http_error(exc) from exc
    return {"files":save_files(project_id,sources)}

@app.post("/api/v1/projects/{project_id}/audits")
def run_project_audit(project_id: str):
    row=get_project(project_id)
    if row is None: raise HTTPException(404,"Project not found")
    files=json.loads(row[2])
    if not files: raise HTTPException(422,"Project has no source files")
    try: result=analyze(files)
    except EngineNotConfigured as exc: raise HTTPException(503,str(exc)) from exc
    except Exception as exc:
        # Do not leak provider credentials, prompts, or source through errors.
        raise HTTPException(502,"Audit engine failed; check server logs") from exc
    return {"status":result.status,"report_markdown":result.report,"agents":result.agent_results,"findings":[],"findings_status":"structured_parsing_not_implemented"}
