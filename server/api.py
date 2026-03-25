import os
import json
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import datetime
import sqlite3
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

# lazily import heavy pipeline to avoid startup failures when optional deps
# (like spaCy) are not installed. import inside handlers that need it.
run_pipeline = None
from server import ai_visibility
from server import ai_analysis
from server import job_queue
from server import keyword_engine
from server import users as user_mgmt
from server import search_intel
from fastapi import WebSocket
import asyncio

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', str(Path(__file__).resolve().parent.parent / 'output')))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='GEO Platform API')

# Serve frontend static files
frontend_dir = Path(__file__).resolve().parent.parent / 'frontend'
app.mount('/static', StaticFiles(directory=str(frontend_dir)), name='static')

class CrawlRequest(BaseModel):
    url: str
    org_name: str
    org_url: str
    max_pages: int = 3
    runs: int = 1
    api_keys: Optional[dict] = None

class RecommendationRequest(BaseModel):
    api_keys: Optional[dict] = None
    job_id: Optional[int] = None
    extra_context: Optional[dict] = None

class AnalysisRequest(BaseModel):
    api_keys: Optional[dict] = None
    job_id: Optional[int] = None

@app.post('/api/crawl')
async def api_crawl(req: CrawlRequest):
    global run_pipeline
    if run_pipeline is None:
        try:
            from src.main import run_pipeline as _rp
            run_pipeline = _rp
        except Exception as e:
            return JSONResponse({'ok': False, 'error': 'pipeline not available: ' + str(e)}, status_code=500)
    # runs: perform multiple runs and average scores, snapshot first run
    runs = max(1, req.runs or 1)
    run_results = []
    timestamps = []
    scores = []
    breakdowns = []
    audit_objs = []
    try:
        for i in range(runs):
            ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            subdir = OUTPUT_DIR / f"run-{ts}-{i+1}"
            res = run_pipeline(req.url, req.org_name, req.org_url, max_pages=req.max_pages, output_dir=subdir)
            # load created audit
            audit_path = Path(res['audit_path'])
            with open(audit_path, 'r', encoding='utf-8') as f:
                audit_obj = json.load(f)
            audit_objs.append(audit_obj)

            # Infer brand name if generic for visibility check
            org_name_for_visibility = req.org_name
            if not org_name_for_visibility or org_name_for_visibility == 'Company':
                pages_for_inference = audit_obj.get('pages', [])
                inferred = ai_analysis.infer_brand_name(pages_for_inference)
                if inferred and inferred != 'Company':
                    org_name_for_visibility = inferred
                    # Update audit_obj with inferred name for consistency
                    audit_obj['org_name'] = inferred
            
            # run AI visibility (Perplexity) for this run and attach; fallback to OpenAI visibility
            queries = [f"What is {org_name_for_visibility}?", f"Best services for {org_name_for_visibility}"]
            perf = ai_visibility.check_perplexity(org_name_for_visibility, queries)
            if not perf.get('enabled') and perf.get('reason') == 'PERPLEXITY_KEY not set':
                # try OpenAI fallback
                try:
                    perf = ai_visibility.check_openai_visibility(org_name_for_visibility, queries)
                    perf['fallback'] = 'openai'
                except Exception:
                    pass
            audit_obj['ai_visibility'] = perf
            # overwrite audit with ai visibility included
            with open(audit_path, 'w', encoding='utf-8') as f:
                json.dump(audit_obj, f, ensure_ascii=False, indent=2)

            # compute geo score for this run
            score = ai_analysis.compute_geo_score(audit_obj.get('pages', []), audit=audit_obj, ai_visibility=perf)
            scores.append(score['score'])
            breakdowns.append(score['breakdown'])
            run_results.append({ 'ts': ts, 'audit_path': str(audit_path), 'geo_score': score })
            timestamps.append(ts)

        # snapshot first run pages for deterministic reference
        snap_ts = timestamps[0]
        snap_src = Path(run_results[0]['audit_path'])
        snap_dst = OUTPUT_DIR / f"snapshot-{snap_ts}.json"
        with open(snap_src, 'r', encoding='utf-8') as fsrc, open(snap_dst, 'w', encoding='utf-8') as fdst:
            fdst.write(fsrc.read())

        # Update the main audit/analysis files so UI endpoints (`/api/results`) read latest data
        try:
            # copy snapshot to output/audit.json
            audit_main = OUTPUT_DIR / 'audit.json'
            with open(snap_dst, 'r', encoding='utf-8') as s, open(audit_main, 'w', encoding='utf-8') as m:
                m.write(s.read())

            # generate and save aggregated analysis (OpenAI/Groq) and geo_score based on snapshot
            try:
                with open(audit_main, 'r', encoding='utf-8') as f:
                    audit_obj = json.load(f)
                pages = audit_obj.get('pages', [])
                analysis = ai_analysis.analyze_pages(pages)
                geo_score = ai_analysis.compute_geo_score(pages, audit=audit_obj, ai_visibility=audit_obj.get('ai_visibility'))
                analysis_out = { 'analysis': analysis, 'geo_score': geo_score }
                with open(OUTPUT_DIR / 'analysis.json', 'w', encoding='utf-8') as fa:
                    json.dump(analysis_out, fa, ensure_ascii=False, indent=2)
                # also save a top-level analysis.json for backwards compatibility
            except Exception:
                pass
        except Exception:
            pass

        # compute aggregated stats
        import statistics
        mean_score = int(round(statistics.mean(scores)))
        median_score = int(round(statistics.median(scores)))
        variance = float(statistics.pstdev(scores))

        history_path = OUTPUT_DIR / 'history.json'
        history = []
        if history_path.exists():
            try:
                history = json.loads(history_path.read_text(encoding='utf-8'))
            except Exception:
                history = []
        entry = {
            'timestamp': timestamps[0],
            'url': req.url,
            'org_name': req.org_name,
            'runs': runs,
            'scores': scores,
            'mean': mean_score,
            'median': median_score,
            'variance': variance,
            'runs_info': run_results
        }
        history.append(entry)
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')

        return { 'ok': True, 'message': 'crawl completed', 'mean_score': mean_score, 'median_score': median_score, 'variance': variance, 'history_entry': entry }
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class JobRequest(BaseModel):
    url: str
    org_name: str
    org_url: str
    max_pages: int = 3
    runs: int = 1


@app.post('/api/jobs')
async def api_enqueue(job: JobRequest, background_tasks: BackgroundTasks):
    try:
        # attach user if Authorization bearer token present
        user_id = None
        company_id = None
        auth = None
        try:
            from server import users as user_mgmt
            auth = Request
        except Exception:
            pass
        # read header from context if available
        try:
            token = None
            if 'authorization' in job.__dict__:
                token = job.__dict__.get('authorization')
        except Exception:
            token = None
        # FastAPI request headers are not directly available here; attempt to read from global request state
        from fastapi import Depends
        # fallback: inspect the incoming request via starlette's Request if passed in
        try:
            # Use the current request from context (this handler doesn't receive Request by default)
            pass
        except Exception:
            pass

        # Simpler approach: if client provided 'Authorization' header, it will be available via Request object.
        # For now, enqueue without user association; clients can call /api/jobs/claim or we can extend later.
        jid = job_queue.enqueue_job(job.url, job.org_name, job.org_url, job.max_pages, job.runs)
        
        # Dispatch background task immediately
        from server.worker import process_job
        job_data = job_queue.get_job(jid)
        if job_data:
            background_tasks.add_task(process_job, job_data)
            
        return {'ok': True, 'job_id': jid}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/jobs')
async def api_list_jobs():
    try:
        data = job_queue.list_jobs()
        return {'ok': True, 'jobs': data}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/jobs/{job_id}')
async def api_get_job(job_id: int):
    try:
        job = job_queue.get_job(job_id)
        if not job:
            return JSONResponse({'ok': False, 'error': 'not found'}, status_code=404)
        # parse progress JSON
        try:
            job['progress'] = json.loads(job.get('progress') or '{}')
        except Exception:
            job['progress'] = {}
        return {'ok': True, 'job': job}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.websocket('/ws/jobs/{job_id}')
async def ws_job_progress(ws: WebSocket, job_id: int):
    await ws.accept()
    last_updated = None
    try:
        while True:
            job = job_queue.get_job(job_id)
            if not job:
                # send a not-found once then keep waiting in case job appears
                try:
                    await ws.send_json({'ok': False, 'error': 'job not found'})
                except Exception:
                    pass
                await asyncio.sleep(1)
                continue

            # normalize progress and datetime fields for JSON
            try:
                prog = job.get('progress')
                if isinstance(prog, str):
                    try:
                        job['progress'] = json.loads(prog or '{}')
                    except Exception:
                        job['progress'] = {}
                else:
                    job['progress'] = prog or {}
            except Exception:
                job['progress'] = {}

            # convert timestamps to ISO strings
            for dt_key in ('created_at', 'updated_at'):
                try:
                    val = job.get(dt_key)
                    if hasattr(val, 'isoformat'):
                        job[dt_key] = val.isoformat()
                    else:
                        job[dt_key] = str(val) if val is not None else None
                except Exception:
                    job[dt_key] = str(job.get(dt_key))

            updated = job.get('updated_at')
            if updated != last_updated:
                last_updated = updated
                try:
                    await ws.send_json({'ok': True, 'job': job})
                except Exception:
                    # if sending fails (e.g., client gone), break loop
                    break
            await asyncio.sleep(1)
    finally:
        try:
            await ws.close()
        except Exception:
            pass

@app.get('/api/jobs/{job_id}/results')
async def api_job_results(job_id: int):
    job = job_queue.get_job(job_id)
    if not job:
        return JSONResponse({'ok': False, 'error': 'not found'}, status_code=404)
    result_path = job.get('result_path')
    if not result_path:
        return JSONResponse({'ok': False, 'error': 'no results yet'}, status_code=400)
    out = {'ok': True, 'job_id': job_id}
    audit_path = Path(result_path) / 'audit.json'
    analysis_path = Path(result_path) / 'analysis.json'
    schema_path = Path(result_path) / 'schema.jsonld'
    if audit_path.exists():
        out['audit'] = json.loads(audit_path.read_text(encoding='utf-8'))
    if analysis_path.exists():
        out['analysis'] = json.loads(analysis_path.read_text(encoding='utf-8'))
    if schema_path.exists():
        out['schema'] = schema_path.read_text(encoding='utf-8')
    return out


@app.get('/api/results')
async def api_results(ts: str | None = None):
    if ts:
        snapshot_path = OUTPUT_DIR / f'snapshot-{ts}.json'
        if snapshot_path.exists():
            try:
                return {'audit': json.loads(snapshot_path.read_text(encoding='utf-8'))}
            except Exception as e:
                return JSONResponse({'ok': False, 'error': f'Failed to load snapshot: {str(e)}'}, status_code=500)
    
    audit_path = OUTPUT_DIR / 'audit.json'
    schema_path = OUTPUT_DIR / 'schema.jsonld'
    out = {}
    if audit_path.exists():
        out['audit'] = json.loads(audit_path.read_text(encoding='utf-8'))
    if schema_path.exists():
        out['schema'] = schema_path.read_text(encoding='utf-8')
    return out

@app.get('/')
async def index():
    index_file = frontend_dir / 'index.html'
    if index_file.exists():
        return FileResponse(str(index_file), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
    return {'ok': True}


@app.get('/recommendations.html')
async def recommendations_page():
    rec_file = frontend_dir / 'recommendations.html'
    if rec_file.exists():
        return FileResponse(str(rec_file), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
    return JSONResponse({'ok': False, 'error': 'recommendations page not found'}, status_code=404)


@app.get('/jobs.html')
async def jobs_page():
    f = frontend_dir / 'jobs.html'
    if f.exists():
        return FileResponse(str(f), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
    return JSONResponse({'ok': False, 'error': 'jobs page not found'}, status_code=404)


@app.get('/search.html')
async def search_page():
    f = frontend_dir / 'search.html'
    if f.exists():
        return FileResponse(str(f), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
    return JSONResponse({'ok': False, 'error': 'search page not found'}, status_code=404)


@app.get('/content')
@app.get('/content_v2.html')
async def content_page_v2():
    f = frontend_dir / 'content_v2.html'
    if f.exists():
        return FileResponse(str(f), headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})
    return JSONResponse({'ok': False, 'error': 'content page not found'}, status_code=404)


@app.get('/theme.css')
async def theme_css_file():
    f = frontend_dir / 'theme.css'
    if f.exists():
        return FileResponse(str(f))
    return JSONResponse({'ok': False, 'error': 'theme.css not found'}, status_code=404)


@app.get('/api/jobs/{job_id}/report')
async def api_job_report(job_id: int):
    job = job_queue.get_job(job_id)
    if not job:
        return JSONResponse({'ok': False, 'error': 'job not found'}, status_code=404)
    result_path = job.get('result_path')
    if not result_path:
        return JSONResponse({'ok': False, 'error': 'job result not ready'}, status_code=400)
    from server import reports
    html = reports.build_html_report(result_path)
    return JSONResponse({'ok': True, 'report_html': html})


@app.get('/api/jobs/{job_id}/report.pdf')
async def api_job_report_pdf(job_id: int):
    job = job_queue.get_job(job_id)
    if not job:
        return JSONResponse({'ok': False, 'error': 'job not found'}, status_code=404)
    result_path = job.get('result_path')
    if not result_path:
        return JSONResponse({'ok': False, 'error': 'job result not ready'}, status_code=400)
    from server import reports
    html = reports.build_html_report(result_path)
    out_pdf = Path(result_path) / f'report-{job_id}.pdf'
    ok = reports.try_render_pdf(html, out_pdf)
    if ok and out_pdf.exists():
        return FileResponse(str(out_pdf), media_type='application/pdf')
    # fallback: return HTML as text for user to save
    return JSONResponse({'ok': True, 'report_html': html})


@app.get('/api/jobs/{job_id}/keywords')
async def api_job_keywords(job_id: int, enrich: bool = True, analytics: bool = False):
    try:
        job = job_queue.get_job(job_id)
        if not job:
            return JSONResponse({'ok': False, 'error': 'job not found'}, status_code=404)
        result_path = job.get('result_path')
        if not result_path:
            return JSONResponse({'ok': False, 'error': 'job result not ready'}, status_code=400)
        audit_path = Path(result_path) / 'audit.json'
        if not audit_path.exists():
            return JSONResponse({'ok': False, 'error': 'audit.json not found in result_path'}, status_code=404)
        with open(audit_path, 'r', encoding='utf-8') as f:
            audit = json.load(f)
        result = keyword_engine.extract_keywords_from_audit(audit, top_n=40, enrich=enrich, analytics=analytics)
        
        if analytics:
            return {'ok': True, 'analytics': result}
        else:
            return {'ok': True, 'keywords': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class UserRegister(BaseModel):
    email: str
    password: str
    company_id: int | None = None


class CompanyRegister(BaseModel):
    name: str
    domain: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post('/api/companies/register')
async def api_register_company(req: CompanyRegister):
    try:
        cid = user_mgmt.create_company(req.name, req.domain)
        return {'ok': True, 'company_id': cid}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/users/register')
async def api_register_user(req: UserRegister):
    try:
        uid = user_mgmt.create_user(req.email, req.password, company_id=req.company_id)
        return {'ok': True, 'user_id': uid}
    except sqlite3.IntegrityError:
        return JSONResponse({'ok': False, 'error': 'email already exists'}, status_code=400)
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/users/login')
async def api_login(req: LoginRequest):
    try:
        user = user_mgmt.authenticate_user(req.email, req.password)
        if not user:
            return JSONResponse({'ok': False, 'error': 'invalid credentials'}, status_code=401)
        token = user_mgmt.make_token(user['id'])
        return {'ok': True, 'token': token, 'user': user}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/users/me')
async def api_me(request: Request):
    auth = request.headers.get('authorization') or request.headers.get('Authorization')
    if not auth or not auth.lower().startswith('bearer '):
        return JSONResponse({'ok': False, 'error': 'missing token'}, status_code=401)
    token = auth.split(' ',1)[1].strip()
    uid = user_mgmt.verify_token(token)
    if not uid:
        return JSONResponse({'ok': False, 'error': 'invalid token'}, status_code=401)
    u = user_mgmt.get_user(uid)
    if not u:
        return JSONResponse({'ok': False, 'error': 'user not found'}, status_code=404)
    return {'ok': True, 'user': u}


@app.post('/api/analyze')
async def api_analyze(req: AnalysisRequest = None):
    api_keys = req.api_keys if req else {}
    job_id = req.job_id if req else None

    # Resolve audit path: job-specific first, then global fallback
    if job_id:
        job = job_queue.get_job(job_id)
        if not job:
            return JSONResponse({'ok': False, 'error': f'job {job_id} not found'}, status_code=404)
        result_path = job.get('result_path')
        if not result_path:
            return JSONResponse({'ok': False, 'error': f'job {job_id} not completed yet'}, status_code=400)
        audit_path = Path(result_path) / 'audit.json'
        analysis_out_path = Path(result_path) / 'analysis.json'
    else:
        audit_path = OUTPUT_DIR / 'audit.json'
        analysis_out_path = OUTPUT_DIR / 'analysis.json'

    if not audit_path.exists():
        return JSONResponse({'ok': False, 'error': 'no audit found; run crawl first'}, status_code=400)

    with open(audit_path, 'r', encoding='utf-8') as f:
        audit = json.load(f)
    pages = audit.get('pages', [])
    
    # Pass user-provided keys to analysis
    analysis = ai_analysis.analyze_pages(pages, api_keys=api_keys)

    # Re-run AI visibility if keys provided to ensure "Visibility Check" works
    ai_vis = audit.get('ai_visibility')
    if api_keys:
        org_name = audit.get('org_name', 'Company')
        queries = [f"What is {org_name}?", f"Best services for {org_name}"]
        # Try Perplexity if key exists, otherwise OpenAI
        if api_keys.get('perplexity'):
            ai_vis = ai_visibility.check_perplexity(org_name, queries, api_key=api_keys.get('perplexity'))
        elif api_keys.get('openai'):
            ai_vis = ai_visibility.check_openai_visibility(org_name, queries, api_key=api_keys.get('openai'))
        audit['ai_visibility'] = ai_vis
        # Save updated audit
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)

    from server import geo_services
    
    # ── Enhanced Visibility Score v2 (API Based) ────────────────────────────────
    org_name = audit.get('org_name') or ai_analysis.infer_brand_name(pages)
    
    # Fetch real search results
    searches = []
    serp_key = api_keys.get("SERPAPI_KEY") if api_keys else None
    zen_key = api_keys.get("ZENSERP_KEY") if api_keys else None
    
    core_queries = [f"{org_name}", f"تحميل {org_name}", f"{org_name} review"]
    for cq in core_queries[:2]:
        s_res = geo_services._serp_api_search(cq, api_key=serp_key)
        if not s_res:
            s_res = geo_services._zenserp_search(cq, api_key=zen_key)
        if s_res:
            searches.append(s_res)

    # ── Competitor Insight Enrichment ──────────────────────────────────────────
    comp_insight = {}
    try:
        comp_insight = geo_services.get_competitor_insights(org_name, audit.get('url'), api_keys=api_keys)
    except Exception:
        pass

    # Hybrid Score Calculation (v2)
    ai_mentions = ai_vis.get("mentions", 0) if ai_vis else 0
    total_queries = ai_vis.get("total_queries", 1) if ai_vis else 1
    traffic_est = comp_insight.get("monthly_visits", "unknown")
    
    geo_v2 = geo_services.calculate_visibility_score_v2(
        org_name, searches, ai_mentions, total_queries, traffic_est
    )
    
    geo = ai_analysis.compute_geo_score(pages, audit=audit, ai_visibility=ai_vis)
    geo["v2"] = geo_v2 # Combined 40/40/20 score

    analysis_out = { 'analysis': analysis, 'geo_score': geo, 'competitor_insight': comp_insight }
    
    with open(analysis_out_path, 'w', encoding='utf-8') as fa:
        json.dump(analysis_out, fa, ensure_ascii=False, indent=2)

    return { 'ok': True, 'analysis': analysis, 'geo_score': geo, 'competitor_insight': comp_insight }


@app.get('/api/history')
async def api_history():
    history_path = OUTPUT_DIR / 'history.json'
    if not history_path.exists():
        return { 'ok': True, 'history': [] }
    try:
        data = json.loads(history_path.read_text(encoding='utf-8'))
        return { 'ok': True, 'history': data }
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class ActivateRequest(BaseModel):
    ts: str
    api_keys: Optional[dict] = None


@app.post('/api/history/activate')
async def api_activate_history(req: ActivateRequest):
    """
    Switch the 'active' research to a historical snapshot.
    This overwrites audit.json and triggers a re-analysis.
    """
    try:
        ts = req.ts
        snapshot_path = OUTPUT_DIR / f'snapshot-{ts}.json'
        if not snapshot_path.exists():
            return JSONResponse({'ok': False, 'error': f'Snapshot {ts} not found'}, status_code=404)

        # 1. Update audit.json
        audit_main = OUTPUT_DIR / 'audit.json'
        with open(snapshot_path, 'r', encoding='utf-8') as s, open(audit_main, 'w', encoding='utf-8') as m:
            audit_obj = json.load(s)
            json.dump(audit_obj, m, ensure_ascii=False, indent=2)

        # 2. Trigger analysis and compute score
        pages = audit_obj.get('pages', [])
        api_keys = req.api_keys or {}
        
        # Pass user-provided keys to analysis
        analysis_data = ai_analysis.analyze_pages(pages, api_keys=api_keys)
        
        # If brand name is generic, infer it
        org_name = audit_obj.get('org_name', 'Company')
        if not org_name or org_name == 'Company':
            inferred = ai_analysis.infer_brand_name(pages)
            if inferred and inferred != 'Company':
                org_name = inferred
                audit_obj['org_name'] = org_name
                # Re-save with inferred name
                with open(audit_main, 'w', encoding='utf-8') as f:
                    json.dump(audit_obj, f, ensure_ascii=False, indent=2)

        ai_vis = audit_obj.get('ai_visibility')
        # Re-run visibility if keys provided
        if api_keys and (api_keys.get('perplexity') or api_keys.get('openai')):
            queries = [f"What is {org_name}?", f"Best services for {org_name}"]
            if api_keys.get('perplexity'):
                ai_vis = ai_visibility.check_perplexity(org_name, queries, api_key=api_keys['perplexity'])
            elif api_keys.get('openai'):
                ai_vis = ai_visibility.check_openai_visibility(org_name, queries, api_key=api_keys.get('openai'))
            audit_obj['ai_visibility'] = ai_vis
            with open(audit_main, 'w', encoding='utf-8') as f:
                json.dump(audit_obj, f, ensure_ascii=False, indent=2)

        geo_score = ai_analysis.compute_geo_score(pages, audit=audit_obj, ai_visibility=ai_vis)
        
        # 3. Save analysis.json
        full_report = { 'analysis': analysis_data, 'geo_score': geo_score }
        analysis_path = OUTPUT_DIR / 'analysis.json'
        with open(analysis_path, 'w', encoding='utf-8') as fa:
            json.dump(full_report, fa, ensure_ascii=False, indent=2)

        # 4. Generate Strategic Intelligence Report for the newly activated data
        # This ensures the Competitive Intelligence Matrix updates immediately
        try:
            from server import search_intelligence
            report = search_intelligence.run_complete_analysis(pages, source_url=audit_obj.get('url', 'http://example.com'), api_keys=api_keys)
        except Exception as e:
            print(f"Intelligence sync error: {e}")
            report = None

        return { 
            'ok': True, 
            'message': f'Research {ts} activated successfully',
            'org_name': org_name,
            'pages_count': len(pages),
            'report': report
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/recommendations')
async def api_recommendations(req: RecommendationRequest = None):
    # load analysis and audit results then produce recommendations
    api_keys = req.api_keys if req else {}
    job_id = req.job_id if req else None
    extra_context = req.extra_context if (req and req.extra_context) else {}

    # Resolve paths: prefer job-specific result_path, fall back to global output/
    if job_id:
        job = job_queue.get_job(job_id)
        if not job:
            return JSONResponse({'ok': False, 'error': f'job {job_id} not found'}, status_code=404)
        result_path = job.get('result_path')
        if not result_path:
            return JSONResponse({'ok': False, 'error': f'job {job_id} has no results yet — wait for it to complete'}, status_code=400)
        audit_path = Path(result_path) / 'audit.json'
        analysis_path = Path(result_path) / 'analysis.json'
    else:
        audit_path = OUTPUT_DIR / 'audit.json'
        analysis_path = OUTPUT_DIR / 'analysis.json'

    if not audit_path.exists():
        return JSONResponse({'ok': False, 'error': 'no audit found — run a crawl first'}, status_code=400)
        
    with open(audit_path, 'r', encoding='utf-8') as f:
        audit = json.load(f)
    
    pages = audit.get('pages', [])

    # If keys are provided, we should probably re-run analysis to fill in the "Visibility" and "AI Analysis" gaps
    if api_keys:
        # Re-run visibility if brand changed or results are missing
        old_org = audit.get('org_name', 'Company')
        org_name = old_org
        if not org_name or org_name == 'Company':
            inferred = ai_analysis.infer_brand_name(pages)
            if inferred and inferred != 'Company':
                org_name = inferred
                audit['org_name'] = org_name
            
        queries = [f"What is {org_name}?", f"Best services for {org_name}"]
        ai_vis = audit.get('ai_visibility')
        
        # If brand name improved OR visibility is missing/demo, re-run it
        needs_visibility = (org_name != old_org) or not ai_vis or not ai_vis.get('enabled')
        if needs_visibility and (api_keys.get('perplexity') or api_keys.get('openai')):
            if api_keys.get('perplexity'):
                ai_vis = ai_visibility.check_perplexity(org_name, queries, api_key=api_keys['perplexity'])
            elif api_keys.get('openai'):
                ai_vis = ai_visibility.check_openai_visibility(org_name, queries, api_key=api_keys.get('openai'))
            audit['ai_visibility'] = ai_vis
        # Re-run analysis
        analysis_data = ai_analysis.analyze_pages(pages, api_keys=api_keys)
        geo_score = ai_analysis.compute_geo_score(pages, audit=audit, ai_visibility=ai_vis)
        
        # Save updated results
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump({ 'analysis': analysis_data, 'geo_score': geo_score }, f, ensure_ascii=False, indent=2)
    else:
        # Just load existing
        if not analysis_path.exists():
            # Trigger basic analysis if missing
            analysis_data = ai_analysis.analyze_pages(pages)
            geo_score = ai_analysis.compute_geo_score(pages, audit=audit, ai_visibility=audit.get('ai_visibility'))
        else:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                ana_obj = json.load(f)
                analysis_data = ana_obj.get('analysis')
                geo_score = ana_obj.get('geo_score')

    recs = ai_analysis.generate_recommendations(pages, geo_score=geo_score, api_keys=api_keys, ai_analysis_results=analysis_data, extra_context=extra_context)
    
    return {
        'ok': True,
        'recommendations': recs,
        'audit': audit,
        'ai_visibility': audit.get('ai_visibility'),
        'analysis': analysis_data,
        'geo_score': geo_score
    }


class KeywordsRequest(BaseModel):
    url: str
    max_pages: int = 1
    api_keys: Optional[dict] = None


@app.post('/api/keywords')
async def api_keywords(req: KeywordsRequest, enrich: bool = True, analytics: bool = False):
    try:
        # try to fetch pages via crawler (will fallback to requests)
        from src import crawler
        pages = crawler.crawl_seed(req.url, max_pages=req.max_pages)
        # build a minimal audit-like object
        audit_obj = {'pages': pages}
        from server import keyword_engine
        result = keyword_engine.extract_keywords_from_audit(audit_obj, top_n=40, enrich=enrich, analytics=analytics)
        
        if analytics:
            # Return full analytics report
            return {'ok': True, 'analytics': result, 'pages': [{'url': p.get('url'), 'title': p.get('title')} for p in pages]}
        else:
            # Return simple keyword list
            return {'ok': True, 'keywords': result, 'pages': [{'url': p.get('url'), 'title': p.get('title')} for p in pages]}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/test/keywords')
async def api_test_keywords():
    """Test endpoint to verify keyword extraction works."""
    try:
        from src import crawler
        from server.keyword_engine import extract_keywords_from_audit
        
        # Test with abayanoir
        pages = crawler.crawl_seed('https://abayanoir.com', max_pages=1)
        audit = {'pages': pages}
        
        # Simple mode
        simple = extract_keywords_from_audit(audit, top_n=5, enrich=False, analytics=False)
        
        # Analytics mode
        analytics = extract_keywords_from_audit(audit, top_n=5, enrich=False, analytics=True)
        
        return {
            'ok': True,
            'simple_keywords': simple,
            'analytics_type': str(type(analytics)),
            'analytics_summary': analytics.get('summary') if isinstance(analytics, dict) else 'NOT A DICT',
            'pages_crawled': len(pages)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/search/intelligence')
async def api_search_intelligence(req: KeywordsRequest, enrich: bool = True):
    """Complete search intelligence analysis with keywords, competitors, and recommendations."""
    try:
        from src import crawler
        from server import search_intelligence
        
        # Crawl pages
        pages = crawler.crawl_seed(req.url, max_pages=req.max_pages)
        
        # Ensure pages is a list
        if not isinstance(pages, list):
            pages = [pages] if pages else []
        
        # Run complete analysis
        report = search_intelligence.run_complete_analysis(pages, req.url, enrich_data=enrich, api_keys=req.api_keys)
        
        return {'ok': True, 'report': report}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/export/keywords/csv')
async def api_export_keywords_csv(req: KeywordsRequest, enrich: bool = True):
    """Export keywords to CSV format."""
    try:
        from src import crawler
        from server import search_intelligence
        import csv
        from io import StringIO
        from fastapi.responses import StreamingResponse
        
        # Crawl and analyze
        pages = crawler.crawl_seed(req.url, max_pages=req.max_pages)
        if not isinstance(pages, list):
            pages = [pages] if pages else []
        
        report = search_intelligence.run_complete_analysis(pages, req.url, enrich_data=enrich)
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Keyword', 'Count', 'Density (%)', 'Volume', 'CPC ($)', 'Competition', 'Classification'])
        
        # Primary keywords
        for kw in report['keyword_results']['classification']['primary']['keywords']:
            writer.writerow([
                kw['kw'],
                kw['count'],
                kw.get('density', 'N/A'),
                kw.get('volume', 'N/A'),
                kw.get('cpc', 'N/A'),
                kw.get('competition', 'N/A'),
                'Primary'
            ])
        
        # Secondary keywords
        for kw in report['keyword_results']['classification']['secondary']['keywords']:
            writer.writerow([
                kw['kw'],
                kw['count'],
                kw.get('density', 'N/A'),
                kw.get('volume', 'N/A'),
                kw.get('cpc', 'N/A'),
                kw.get('competition', 'N/A'),
                'Secondary'
            ])
        
        # Long-tail keywords
        for kw in report['keyword_results']['classification']['long_tail']['keywords']:
            writer.writerow([
                kw['kw'],
                kw['count'],
                kw.get('density', 'N/A'),
                kw.get('volume', 'N/A'),
                kw.get('cpc', 'N/A'),
                kw.get('competition', 'N/A'),
                'Long-tail'
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=keywords_{req.url.replace('https://', '').replace('/', '_')}.csv"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/search/competitors')
async def api_search_competitors(req: KeywordsRequest):
    try:
        from src import crawler
        from server import competitor_analysis
        
        pages = crawler.crawl_seed(req.url, max_pages=req.max_pages)
        competitors = competitor_analysis.detect_competitors(pages, req.url, min_mentions=1)
        summary = competitor_analysis.get_competitor_summary(competitors)
        
        return {
            'ok': True, 
            'result': {
                'competitors': competitors,
                'summary': summary,
                'pages_analyzed': len(pages)
            }
        }
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/search/gsc')
async def api_search_gsc(site: str, start: str, end: str):
    try:
        res = search_intel.gsc_query(site, start, end)
        return {'ok': True, 'result': res}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


# ── AI Content Engine ──────────────────────────────────────────────────────────

class ArticleRequest(BaseModel):
    keyword: str
    lang: str = 'en'
    target_site: str = ""
    research_insights: list = []
    competitors_content: list = []
    crawl_data: dict = {}
    prefer_backend: str = 'groq'
    api_keys: dict = {}


class OptimizeRequest(BaseModel):
    content: str
    keyword: str
    lang: str = 'en'
    target_site: str = ""
    research_insights: list = []
    crawl_data: dict = {}
    prefer_backend: str = 'groq'
    api_keys: dict = {}


class FaqRequest(BaseModel):
    topic: str
    page_content: str = ''
    lang: str = 'en'
    target_site: str = ""
    research_insights: list = []
    crawl_data: dict = {}
    count: int = 5
    prefer_backend: str = 'groq'
    api_keys: dict = {}


class SemanticRequest(BaseModel):
    content: str
    lang: str = 'en'
    prefer_backend: str = 'groq'
    api_keys: dict = {}


@app.post('/api/content/generate')
async def api_content_generate(req: ArticleRequest):
    try:
        from server import content_engine
        result = content_engine.generate_article(
            req.keyword, lang=req.lang,
            target_site=req.target_site,
            research_insights=req.research_insights,
            competitors_content=req.competitors_content,
            crawl_data=req.crawl_data,
            prefer_backend=req.prefer_backend,
            api_keys=req.api_keys
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/content/optimize')
async def api_content_optimize(req: OptimizeRequest):
    try:
        from server import content_engine
        result = content_engine.optimize_content(
            req.content, req.keyword, lang=req.lang,
            target_site=req.target_site,
            research_insights=req.research_insights,
            crawl_data=req.crawl_data,
            prefer_backend=req.prefer_backend,
            api_keys=req.api_keys
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/content/faqs')
async def api_content_faqs(req: FaqRequest):
    try:
        from server import content_engine
        result = content_engine.generate_faqs(
            req.topic, page_content=req.page_content,
            lang=req.lang, count=req.count,
            target_site=req.target_site,
            research_insights=req.research_insights,
            crawl_data=req.crawl_data,
            prefer_backend=req.prefer_backend,
            api_keys=req.api_keys
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/content/semantic')
async def api_content_semantic(req: SemanticRequest):
    try:
        from server import content_engine
        result = content_engine.semantic_optimize(
            req.content, lang=req.lang,
            prefer_backend=req.prefer_backend,
            api_keys=req.api_keys
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# PAID ADS MANAGEMENT MODULE                                                    
# ═══════════════════════════════════════════════════════════════════════════════
from server import ads_manager, ads_ai

class AdsConnectRequest(BaseModel):
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str
    customer_id: str

class AdsAIRequest(BaseModel):
    api_keys: Optional[dict] = None
    lang: Optional[str] = 'ar'
    service_name: Optional[str] = 'خدمات SEO'
    usp: Optional[str] = 'نتائج مضمونة في 90 يوم'
    target_audience: Optional[str] = 'شركات سعودية'

class CampaignCreateRequest(BaseModel):
    name: str
    budget_usd: float = 5.0
    target_cpa: Optional[float] = None

@app.post('/api/ads/connect')
async def api_ads_connect(req: AdsConnectRequest):
    """Save Google Ads credentials and verify they work."""
    try:
        credentials = {
            'developer_token': req.developer_token,
            'client_id': req.client_id,
            'client_secret': req.client_secret,
            'refresh_token': req.refresh_token,
            'customer_id': req.customer_id
        }
        result = ads_manager.verify_google_connection(credentials)
        if result.get('ok'):
            ads_manager.save_ads_config(credentials)
        return result
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/ads/dashboard')
async def api_ads_dashboard(demo: bool = False, days: int = 30):
    """Return unified KPI dashboard data — uses saved credentials or demo."""
    try:
        credentials = {} if demo else ads_manager.load_ads_config()
        campaigns = ads_manager.get_campaign_performance(credentials, days=days)
        summary = ads_manager.build_ads_summary(campaigns, credentials=credentials)
        return {'ok': True, 'summary': summary, 'campaigns': campaigns}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/ads/keywords')
async def api_ads_keywords(demo: bool = False):
    """Return keyword performance with Quality Scores."""
    try:
        credentials = {} if demo else ads_manager.load_ads_config()
        keywords = ads_manager.get_keyword_performance(credentials)
        return {'ok': True, 'keywords': keywords, 'count': len(keywords)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/ads/search-terms')
async def api_ads_search_terms(demo: bool = False, min_clicks: int = 5):
    """Return search term analysis — converting vs. wasted spend."""
    try:
        credentials = {} if demo else ads_manager.load_ads_config()
        data = ads_manager.get_search_terms(credentials, min_clicks=min_clicks)
        return {'ok': True, 'data': data}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/ads/campaigns')
async def api_ads_create_campaign(req: CampaignCreateRequest):
    """Create a new Google Ads campaign (starts PAUSED for safety)."""
    try:
        credentials = ads_manager.load_ads_config()
        result = ads_manager.create_campaign(
            credentials, req.name, req.budget_usd, req.target_cpa
        )
        return result
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/ads/ai/bid-suggestions')
async def api_ads_bid_suggestions(req: AdsAIRequest):
    """AI-powered bid adjustment recommendations for each keyword."""
    try:
        credentials = ads_manager.load_ads_config()
        keywords = ads_manager.get_keyword_performance(credentials)
        suggestions = ads_ai.ai_bid_suggestion(keywords, api_keys=req.api_keys or {})
        return {'ok': True, 'suggestions': suggestions, 'count': len(suggestions)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/ads/ai/copy')
async def api_ads_generate_copy(req: AdsAIRequest):
    """Generate Arabic + English RSA ad copy using AI."""
    try:
        result = ads_ai.generate_ad_copy(
            service_name=req.service_name or 'خدمات SEO',
            usp=req.usp or 'نتائج مضمونة في 90 يوم',
            target_audience=req.target_audience or 'شركات سعودية',
            lang=req.lang or 'ar',
            api_keys=req.api_keys or {}
        )
        return {'ok': True, 'copy': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/ads/ai/negatives')
async def api_ads_negative_keywords(req: AdsAIRequest):
    """Detect irrelevant search terms and suggest negative keywords."""
    try:
        credentials = ads_manager.load_ads_config()
        search_terms = ads_manager.get_search_terms(credentials)
        result = ads_ai.detect_negative_keywords(search_terms, api_keys=req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/ads/ai/weekly-report')
async def api_ads_weekly_report(req: AdsAIRequest):
    """Generate AI-written weekly performance report in Arabic or English."""
    try:
        credentials = ads_manager.load_ads_config()
        campaigns = ads_manager.get_campaign_performance(credentials)
        keywords = ads_manager.get_keyword_performance(credentials)
        search_terms = ads_manager.get_search_terms(credentials)
        report = ads_ai.generate_weekly_report(
            campaigns, keywords, search_terms,
            api_keys=req.api_keys or {},
            lang=req.lang or 'ar'
        )
        return {'ok': True, 'report': report}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


# ══════════════════════════════════════════════════════════════════════════════
# GEO SERVICES — 6 AI Visibility Services
# ══════════════════════════════════════════════════════════════════════════════
from server import geo_services

class GeoServiceRequest(BaseModel):
    brand: str
    url: Optional[str] = None
    queries: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    brand_variants: Optional[List[str]] = None
    api_keys: Optional[dict] = None

class SimulatorRequest(BaseModel):
    brand: str
    original_content: str
    improved_content: str
    test_queries: List[str]
    api_keys: Optional[dict] = None

@app.post('/api/geo/visibility')
async def api_geo_visibility(req: GeoServiceRequest):
    try:
        queries = req.queries or geo_services.DEFAULT_QUERIES
        result = geo_services.visibility_score(req.brand, queries, req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/recognition')
async def api_geo_recognition(req: GeoServiceRequest):
    try:
        queries = req.queries or geo_services.DEFAULT_QUERIES
        variants = req.brand_variants or [req.brand]
        result = geo_services.brand_recognition(req.brand, variants, queries, req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/sentiment')
async def api_geo_sentiment(req: GeoServiceRequest):
    try:
        queries = req.queries or geo_services.DEFAULT_QUERIES
        result = geo_services.sentiment_analysis(req.brand, queries, req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/competitors')
async def api_geo_competitors(req: GeoServiceRequest):
    try:
        queries = req.queries or geo_services.DEFAULT_QUERIES
        competitors = req.competitors or ['SEMrush', 'Ahrefs', 'Moz']
        result = geo_services.competitor_ranking(req.brand, competitors, queries, req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/regional')
async def api_geo_regional(req: GeoServiceRequest):
    try:
        result = geo_services.geo_regional_analysis(req.brand, req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/fix')
async def api_geo_fix(req: GeoServiceRequest):
    try:
        if not req.url:
            return JSONResponse({'ok': False, 'error': 'url required'}, status_code=400)
        result = geo_services.fix_recommendations(req.url, req.brand, {}, req.api_keys or {})
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/simulate')
async def api_geo_simulate(req: SimulatorRequest):
    try:
        result = geo_services.visibility_simulator(
            req.original_content, req.improved_content,
            req.test_queries, req.brand, req.api_keys or {}
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/geo/suite')
async def api_geo_suite(req: GeoServiceRequest, background_tasks: BackgroundTasks):
    """Run all 6 GEO services at once for a brand."""
    try:
        result = geo_services.run_full_suite(
            req.brand, req.url, req.competitors, req.api_keys or {}
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.get('/geo')
@app.get('/geo_services.html')
@app.get('/geo-toolkit.html')
async def serve_geo_services():
    return FileResponse(str(frontend_dir / 'geo-toolkit.html'))

@app.get('/regional.html')
async def serve_regional_dashboard():
    """Serve the Regional AI Visibility dashboard."""
    return FileResponse(str(frontend_dir / 'regional.html'))

@app.get('/ads')
@app.get('/ads.html')
async def serve_ads_dashboard():
    """Serve the Paid Ads Management dashboard."""
    return FileResponse(str(frontend_dir / 'ads.html'))


# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED FEATURES — Keyword Tracking, Alerts, Scheduler, Bulk, Gap, Email
# ═══════════════════════════════════════════════════════════════════════════════

from server.advanced_features import (
    save_keyword_snapshot, save_geo_score_snapshot,
    get_keyword_trends, get_geo_score_trends,
    check_and_create_alerts, get_alerts, mark_alerts_seen,
    add_scheduled_crawl, list_scheduled_crawls, delete_scheduled_crawl,
    competitor_keyword_gap, bulk_enqueue, send_weekly_report,
    start_scheduler, init_advanced_tables
)

try:
    init_advanced_tables()
    start_scheduler()
except Exception:
    pass


@app.get('/api/tracking/keywords')
async def api_keyword_trends(url: str, keyword: str = None, days: int = 30):
    try:
        return {'ok': True, 'trends': get_keyword_trends(url, keyword, days)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/tracking/geo-score')
async def api_geo_score_trends(url: str, days: int = 90):
    try:
        return {'ok': True, 'trends': get_geo_score_trends(url, days)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/alerts')
async def api_get_alerts(url: str = None, unseen_only: bool = False):
    try:
        alerts = get_alerts(url, unseen_only)
        return {'ok': True, 'alerts': alerts, 'count': len(alerts)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post('/api/alerts/seen')
async def api_mark_alerts_seen(req: dict):
    try:
        mark_alerts_seen(req.get('ids', []))
        return {'ok': True}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class ScheduleRequest(BaseModel):
    url: str
    org_name: str = ''
    org_url: str = ''
    max_pages: int = 3
    frequency: str = 'weekly'


@app.post('/api/schedule')
async def api_add_schedule(req: ScheduleRequest):
    try:
        sid = add_scheduled_crawl(req.url, req.org_name, req.org_url, req.max_pages, req.frequency)
        return {'ok': True, 'schedule_id': sid}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/api/schedule')
async def api_list_schedules():
    try:
        return {'ok': True, 'schedules': list_scheduled_crawls()}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.delete('/api/schedule/{schedule_id}')
async def api_delete_schedule(schedule_id: int):
    try:
        delete_scheduled_crawl(schedule_id)
        return {'ok': True}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class GapRequest(BaseModel):
    your_keywords: list = []
    competitor_url: str
    max_pages: int = 3


@app.post('/api/competitor/gap')
async def api_competitor_gap(req: GapRequest):
    try:
        return {'ok': True, 'gap': competitor_keyword_gap(req.your_keywords, req.competitor_url, req.max_pages)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class BulkRequest(BaseModel):
    urls: list
    org_name: str = ''
    max_pages: int = 2


@app.post('/api/bulk/crawl')
async def api_bulk_crawl(req: BulkRequest):
    try:
        job_ids = bulk_enqueue(req.urls, req.org_name, req.max_pages)
        return {'ok': True, 'job_ids': job_ids, 'count': len(job_ids)}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


class EmailReportRequest(BaseModel):
    to_email: str
    url: str


@app.post('/api/reports/email')
async def api_send_email_report(req: EmailReportRequest):
    try:
        ok = send_weekly_report(req.to_email, req.url)
        if ok:
            return {'ok': True, 'message': f'تم الإرسال إلى {req.to_email}'}
        return JSONResponse({'ok': False, 'error': 'فشل الإرسال — أضف SMTP_HOST و SMTP_USER و SMTP_PASS في .env'}, status_code=400)
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


_SETTINGS_PATH = Path(os.environ.get('OUTPUT_DIR', Path(__file__).resolve().parent.parent / 'output')) / 'settings.json'


def _load_settings() -> dict:
    if _SETTINGS_PATH.exists():
        try:
            return json.loads(_SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    _SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@app.get('/api/settings')
async def api_get_settings():
    s = _load_settings()
    safe = {}
    for k, v in s.items():
        safe[k] = '***' if (v and (k.endswith('_key') or k.endswith('_KEY') or 'pass' in k.lower())) else v
    return {'ok': True, 'settings': safe}


@app.post('/api/settings')
async def api_save_settings(req: dict):
    try:
        current = _load_settings()
        for k, v in req.items():
            if v and v != '***':
                current[k] = v
                os.environ[k.upper()] = v
        _save_settings(current)
        return {'ok': True}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


try:
    for k, v in _load_settings().items():
        if v and v != '***':
            os.environ.setdefault(k.upper(), v)
except Exception:
    pass


# ── Competitor Intelligence Analyzer ─────────────────────────────────────────

class CompetitorIntelRequest(BaseModel):
    url: str
    region: str = 'Saudi Arabia'
    industry: str = ''
    count: int = 7
    api_keys: dict = {}


@app.post('/api/competitor/intelligence')
async def api_competitor_intelligence(req: CompetitorIntelRequest):
    try:
        from server.competitor_intel import analyze_competitors
        result = analyze_competitors(
            req.url, region=req.region,
            industry=req.industry, count=req.count,
            api_keys=req.api_keys
        )
        return {'ok': True, 'result': result}
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.get('/competitor-intel.html')
@app.get('/competitor-intel')
async def serve_competitor_intel():
    return FileResponse(str(frontend_dir / 'competitor-intel.html'))
