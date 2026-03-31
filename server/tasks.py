from server.celery_app import celery_app
from server.worker import process_job

@celery_app.task(name="server.tasks.run_background_pipeline", bind=True, max_retries=3)
def run_background_pipeline(self, job_dict):
    """
    Enterprise entrypoint for background pipeline crawls.
    Accepts job dictionary and triggers the extraction/analysis pipeline.
    """
    try:
        # job_dict should contain 'id', 'url', 'org_name', etc.
        process_job(job_dict)
        return {"status": "success", "job_id": job_dict.get("id")}
    except Exception as exc:
        # Retry with exponential backoff on failure
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
