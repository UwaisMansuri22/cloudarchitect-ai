from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os, time, uuid, boto3, json
from datetime import datetime, timezone

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

# ── Rate limiting ─────────────────────────────────────────────

_rate_table = None

def _get_rate_table():
    global _rate_table
    if _rate_table is None:
        name = os.getenv('RATE_LIMIT_TABLE')
        if not name:
            return None
        _rate_table = boto3.resource('dynamodb').Table(name)
    return _rate_table

def _check_rate_limit(ip: str) -> int:
    table = _get_rate_table()
    if table is None:
        return 0
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    ttl = int(datetime.now(timezone.utc).replace(hour=23, minute=59, second=59).timestamp()) + 86400
    resp = table.update_item(
        Key={'pk': f"{ip}#{today}"},
        UpdateExpression='ADD #r :one SET #t = if_not_exists(#t, :ttl)',
        ExpressionAttributeNames={'#r': 'requests', '#t': 'ttl'},
        ExpressionAttributeValues={':one': 1, ':ttl': ttl},
        ReturnValues='ALL_NEW'
    )
    return int(resp['Attributes']['requests'])

# ── Jobs table ────────────────────────────────────────────────

_jobs_table = None

def _get_jobs_table():
    global _jobs_table
    if _jobs_table is None:
        name = os.getenv('JOBS_TABLE')
        if not name:
            return None
        _jobs_table = boto3.resource('dynamodb').Table(name)
    return _jobs_table


# ── Background job processor (called when Lambda is async-invoked) ──

def _process_background_job(event: dict):
    job_id = event['job_id']
    description = event['description']
    constraints = event.get('constraints')
    session_id = event.get('session_id', job_id)

    jobs_table = _get_jobs_table()

    def _update_status(status, extra=None):
        if not jobs_table:
            return
        expr = 'SET #s = :s'
        names = {'#s': 'status'}
        vals = {':s': status}
        if extra:
            for k, v in extra.items():
                expr += f', #{k} = :{k}'
                names[f'#{k}'] = k
                vals[f':{k}'] = v
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=vals
        )

    _update_status('processing')

    try:
        start = time.time()
        state = {
            'description': description,
            'constraints': constraints,
            'session_id': session_id,
            'start_time': start,
            'requirements': None,
            'architecture': None,
            'mermaid_diagram': None,
            'cost_estimate': None,
            'security_recommendations': None,
            'terraform_code': None,
            'current_agent': 'requirements',
            'error': None
        }
        result = graph.invoke(state)

        total_cost = sum(
            item.monthly_cost_usd for item in (result.get('cost_estimate') or [])
        )
        arch_result = ArchitectureResult(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            description=description,
            requirements=result['requirements'],
            architecture=result['architecture'],
            mermaid_diagram=result['mermaid_diagram'],
            cost_estimate=result['cost_estimate'] or [],
            total_monthly_cost_usd=total_cost,
            security_recommendations=result['security_recommendations'] or [],
            terraform_code=result['terraform_code'] or '',
            generation_time_seconds=round(time.time() - start, 2)
        )
        _update_status('complete', {'result': arch_result.model_dump_json()})

    except Exception as e:
        _update_status('error', {'error_msg': str(e)})


# ── Routes ────────────────────────────────────────────────────

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
def architect(http_request: Request, request: ArchitectureRequest):
    ip = (http_request.headers.get('x-forwarded-for') or
          (http_request.client.host if http_request.client else 'unknown')).split(',')[0].strip()
    try:
        count = _check_rate_limit(ip)
    except Exception:
        count = 0
    daily_limit = int(os.getenv('DAILY_RATE_LIMIT', '3'))
    if count > daily_limit:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {daily_limit} request{'s' if daily_limit != 1 else ''} per day per IP address.")

    jobs_table = _get_jobs_table()

    # Local dev (no JOBS_TABLE): run synchronously and return full result
    if not jobs_table:
        try:
            start = time.time()
            state = {
                'description': request.description,
                'constraints': request.constraints,
                'session_id': request.session_id or str(uuid.uuid4()),
                'start_time': start,
                'requirements': None, 'architecture': None,
                'mermaid_diagram': None, 'cost_estimate': None,
                'security_recommendations': None, 'terraform_code': None,
                'current_agent': 'requirements', 'error': None
            }
            result = graph.invoke(state)
            total_cost = sum(i.monthly_cost_usd for i in (result.get('cost_estimate') or []))
            return ArchitectureResult(
                session_id=state['session_id'],
                generated_at=datetime.utcnow(),
                description=request.description,
                requirements=result['requirements'],
                architecture=result['architecture'],
                mermaid_diagram=result['mermaid_diagram'],
                cost_estimate=result['cost_estimate'] or [],
                total_monthly_cost_usd=total_cost,
                security_recommendations=result['security_recommendations'] or [],
                terraform_code=result['terraform_code'] or '',
                generation_time_seconds=round(time.time() - start, 2)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Lambda: async path
    job_id = str(uuid.uuid4())
    ttl = int(time.time()) + 86400 * 7
    jobs_table.put_item(Item={'job_id': job_id, 'status': 'pending', 'ttl': ttl})

    boto3.client('lambda').invoke(
        FunctionName=os.environ['AWS_LAMBDA_FUNCTION_NAME'],
        InvocationType='Event',
        Payload=json.dumps({
            'type': 'background_job',
            'job_id': job_id,
            'description': request.description,
            'constraints': request.constraints,
            'session_id': request.session_id or job_id
        }).encode()
    )

    return {'job_id': job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    jobs_table = _get_jobs_table()
    if not jobs_table:
        raise HTTPException(status_code=503, detail="Jobs service unavailable")

    item = jobs_table.get_item(Key={'job_id': job_id}).get('Item')
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")

    status = item.get('status', 'pending')
    resp = {'status': status, 'job_id': job_id}

    if status == 'complete':
        result_json = item.get('result')
        if result_json:
            resp['result'] = json.loads(result_json)
    elif status == 'error':
        resp['error'] = item.get('error_msg', 'Unknown error')

    return resp


@app.get("/terraform/{session_id}")
def download_terraform(session_id: str):
    raise HTTPException(status_code=404, detail="Session not found")


# ── Lambda entry point ────────────────────────────────────────

_mangum = Mangum(app)

def handler(event, context):
    if event.get('type') == 'background_job':
        _process_background_job(event)
        return {'statusCode': 200}
    return _mangum(event, context)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
