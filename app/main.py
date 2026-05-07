from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os, time, uuid
from datetime import datetime

from app.models import ArchitectureRequest, ArchitectureResult
from app.graph import create_graph

app = FastAPI(title="CloudArchitect AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

graph = create_graph()


@app.get("/")
def serve_ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="26" font-size="28">&#x2B21;</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "CloudArchitect AI", "version": "1.0.0"}


@app.post("/architect")
def architect(request: ArchitectureRequest):
    try:
        start = time.time()
        state = {
            "description": request.description,
            "constraints": request.constraints,
            "session_id": request.session_id or str(uuid.uuid4()),
            "start_time": start,
            "requirements": None,
            "architecture": None,
            "mermaid_diagram": None,
            "cost_estimate": None,
            "security_recommendations": None,
            "terraform_code": None,
            "current_agent": "requirements",
            "error": None
        }

        result = graph.invoke(state)

        total_cost = sum(
            item.monthly_cost_usd
            for item in (result.get("cost_estimate") or [])
        )

        return ArchitectureResult(
            session_id=result["session_id"],
            generated_at=datetime.utcnow(),
            description=request.description,
            requirements=result["requirements"],
            architecture=result["architecture"],
            mermaid_diagram=result["mermaid_diagram"],
            cost_estimate=result["cost_estimate"] or [],
            total_monthly_cost_usd=total_cost,
            security_recommendations=result["security_recommendations"] or [],
            terraform_code=result["terraform_code"] or "",
            generation_time_seconds=round(time.time() - start, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/terraform/{session_id}")
def download_terraform(session_id: str):
    raise HTTPException(status_code=404, detail="Session not found")


handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
