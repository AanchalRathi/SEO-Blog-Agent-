from celery_app import celery_app
from crew import CompanyConfig, run_crew
from database import SessionLocal, save_blog, update_job_status, complete_job, fail_job
from utils import get_docs_path


@celery_app.task(name="run_pipeline_task", bind=True, max_retries=2)
def run_pipeline_task(self, job_id: str, req_data: dict):
    
    db = SessionLocal()
    try:
        update_job_status(db, job_id, "running")

        config = CompanyConfig(
            company_name    = req_data["company_name"],
            niche           = req_data["niche"],
            target_audience = req_data["target_audience"],
            competitors     = req_data["competitors"],
            docs_path       = get_docs_path(req_data["company_name"]),
            tone            = req_data["tone"],
            region          = req_data["region"],
            user_query      = req_data["user_query"],
        )

        result = run_crew(config)
        result["company_name"] = req_data["company_name"]
        result["success"] = True

        saved = save_blog(db, result, niche=req_data["niche"])
        complete_job(db, job_id, result, blog_id=saved.id)

    except Exception as e:
        fail_job(db, job_id, error=str(e))
        print(f"[Pipeline] Job {job_id} failed: {e}")
        raise
    finally:
        db.close()
