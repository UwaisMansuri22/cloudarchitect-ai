from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os, time, json, uuid
from datetime import datetime

from app.models import ArchitectureRequest, ArchitectureResult
from app.graph import create_graph

app = FastAPI(title="CloudArchitect AI", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Create graph instance
try:
    graph = create_graph()
except Exception as e:
    print(f"Warning: Graph creation failed - {e}")
    graph = None


@app.get("/")
def serve_ui():
    index_path = os.path.join(os.path.dirname(__file__), "app", "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "UI not available"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="26" font-size="28">&#x2B21;</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "CloudArchitect AI", "version": "1.0.0"}


@app.post("/architect")
def architect(request: ArchitectureRequest):
    if not graph:
        raise HTTPException(status_code=500, detail="Graph not initialized")
    
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
        
        result_state = graph.invoke(state)
        execution_time = time.time() - start
        
        return ArchitectureResult(
            session_id=result_state.get("session_id"),
            requirements=result_state.get("requirements"),
            architecture=result_state.get("architecture"),
            mermaid_diagram=result_state.get("mermaid_diagram"),
            cost_estimate=result_state.get("cost_estimate"),
            security_recommendations=result_state.get("security_recommendations"),
            terraform_code=result_state.get("terraform_code"),
            execution_time=execution_time,
            error=result_state.get("error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)