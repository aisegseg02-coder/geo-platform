"""Background worker CLI to process queued jobs from `server.job_queue`.

Run: `python -m server.worker` from project root.
"""
import time
import os
from server import job_queue
from src.main import run_pipeline
from server import ai_visibility, ai_analysis
import json
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', str(Path(__file__).resolve().parent.parent / 'output')))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def process_job(job):
    jid = job['id']
    # ensure job is claimed
    claimed = job_queue.claim_job(jid)
    if not claimed:
        print(f"Job {jid} not pending; skipping")
        return
    job_queue.update_job(jid, progress={'stage':'started', 'percent':0})
    try:
        out_dir = OUTPUT_DIR / f'job-{jid}'
        out_dir.mkdir(parents=True, exist_ok=True)

        job_queue.update_job(jid, progress={'stage':'crawling', 'percent':10})
        res = run_pipeline(job['url'], job['org_name'], job['org_url'], max_pages=job.get('max_pages',3), output_dir=out_dir)

        # attach AI visibility
        job_queue.update_job(jid, progress={'stage':'ai_visibility', 'percent':50})
        queries = [f"What is {job['org_name']}?", f"Best services for {job['org_name']}"]
        perf = ai_visibility.check_perplexity(job['org_name'], queries)
        if not perf.get('enabled') and perf.get('reason') == 'PERPLEXITY_KEY not set':
            perf = ai_visibility.check_openai_visibility(job['org_name'], queries)

        # write combined audit file
        audit_path = out_dir / 'audit.json'
        with open(audit_path, 'r', encoding='utf-8') as f:
            audit = json.load(f)
        audit['ai_visibility'] = perf
        with open(audit_path, 'w', encoding='utf-8') as f:
            json.dump(audit, f, ensure_ascii=False, indent=2)

        job_queue.update_job(jid, progress={'stage':'analysis', 'percent':75})
        # run analysis and compute geo score
        pages = audit.get('pages', [])
        analysis = ai_analysis.analyze_pages(pages)
        geo = ai_analysis.compute_geo_score(pages, audit=audit, ai_visibility=audit.get('ai_visibility'))
        out = { 'analysis': analysis, 'geo_score': geo }
        
        analysis_path = out_dir / 'analysis.json'
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        # Update the main audit.json and analysis.json so UI `/api/results` sees the latest job
        try:
            main_out = out_dir.parent
            with open(main_out / 'audit.json', 'w', encoding='utf-8') as m_audit:
                m_audit.write(audit_path.read_text(encoding='utf-8'))
            with open(main_out / 'analysis.json', 'w', encoding='utf-8') as m_ana:
                m_ana.write(analysis_path.read_text(encoding='utf-8'))
        except Exception as copy_err:
            print(f"Failed to copy job results to main output dir: {copy_err}")

        job_queue.update_job(jid, status='completed', progress={'stage':'done','percent':100}, result_path=str(out_dir))

        # ── Save tracking snapshots & check alerts ────────────────────────
        try:
            from server.advanced_features import (
                save_keyword_snapshot, save_geo_score_snapshot, check_and_create_alerts
            )
            from server.keyword_engine import extract_keywords_from_audit
            kws = extract_keywords_from_audit({'pages': pages}, top_n=30, enrich=False)
            save_keyword_snapshot(jid, job.get('url', ''), kws if isinstance(kws, list) else kws.get('top_keywords', []))
            save_geo_score_snapshot(jid, job.get('url', ''), geo)
            check_and_create_alerts(jid, job.get('url', ''), geo)
        except Exception as track_err:
            print(f'Tracking error (non-fatal): {track_err}')
    except Exception as e:
        job_queue.update_job(jid, status='failed', progress={'stage':'error','error': str(e)})


def run_worker(poll_interval=3):
    print('Worker started, polling for jobs...')
    while True:
        job = job_queue.claim_next_job()
        if job:
            try:
                print('Processing job', job['id'])
                process_job(job)
            except Exception as e:
                print('Error processing job', job['id'], e)
        else:
            time.sleep(poll_interval)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--job-id', type=int, help='Process a single job id (claim and run)')
    p.add_argument('--poll', type=float, default=3.0, help='Poll interval for worker')
    args = p.parse_args()
    if args.job_id:
        job = job_queue.get_job(args.job_id)
        if not job:
            print('Job not found')
        else:
            process_job(job)
    else:
        run_worker(poll_interval=args.poll)
