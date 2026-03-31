import os
import sys
from pathlib import Path

# Add project root to sys.path so we can import server
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, project_root)

import sqlite3
import json
from datetime import datetime
from server.db import init_db, SessionLocal, Company, User, Job, get_db_session
import hashlib

def generate_request_hash(row):
    """Idempotency check generator string for jobs"""
    base = f"{row.get('url')}-{row.get('org_name')}-{row.get('created_at')}"
    return hashlib.md5(base.encode()).hexdigest()

def migrate():
    print("🚀 Starting Database Migration to SQLAlchemy ORM...")
    init_db()
    
    output_dir = Path(project_root) / 'output'
    
    # 1. Migrate Users & Companies
    users_db = output_dir / 'users.db'
    if users_db.exists():
        conn = sqlite3.connect(str(users_db))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Companies
        try:
            with get_db_session() as db:
                cur.execute("SELECT * FROM companies")
                companies = cur.fetchall()
                migrated_companies = 0
                for row in companies:
                    if not db.query(Company).filter_by(id=row['id']).first():
                        company = Company(
                            id=row['id'],
                            name=row['name'],
                            domain=row['domain'],
                            created_at=datetime.fromtimestamp(row['created_at']) if row['created_at'] else datetime.utcnow()
                        )
                        db.add(company)
                        migrated_companies += 1
                print(f"✅ Companies migrated (Total: {migrated_companies}/{len(companies)})")
        except Exception as e:
            print("⚠️ Companies migration skipped or failed:", e)

        # Users
        try:
            with get_db_session() as db:
                cur.execute("SELECT * FROM users")
                users = cur.fetchall()
                migrated_users = 0
                for row in users:
                    if not db.query(User).filter_by(id=row['id']).first():
                        user = User(
                            id=row['id'],
                            email=row['email'],
                            password_hash=row['password_hash'],
                            role=row['role'],
                            company_id=row['company_id'],
                            created_at=datetime.fromtimestamp(row['created_at']) if row['created_at'] else datetime.utcnow()
                        )
                        db.add(user)
                        migrated_users += 1
                print(f"✅ Users migrated (Total: {migrated_users}/{len(users)})")
        except Exception as e:
            print("⚠️ Users migration failed:", e)
            
        conn.close()

    # 2. Migrate Jobs
    jobs_db = output_dir / 'jobs.db'
    if jobs_db.exists():
        conn = sqlite3.connect(str(jobs_db))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT * FROM jobs")
            for row in cur.fetchall():
                if not db.query(Job).filter_by(id=row['id']).first():
                    # SQLite progress defaults
                    progress = dict()
                    try:
                        progress = json.loads(row['progress'] or "{}")
                    except Exception:
                        pass
                        
                    job = Job(
                        id=row['id'],
                        url=row['url'],
                        org_name=row['org_name'],
                        org_url=row['org_url'],
                        max_pages=row['max_pages'],
                        runs=row['runs'],
                        status=row['status'],
                        progress=progress,
                        result_path=row['result_path'],
                        user_id=row['user_id'] if 'user_id' in row.keys() else None,
                        company_id=row['company_id'] if 'company_id' in row.keys() else None,
                        industry_override=row['industry_override'] if 'industry_override' in row.keys() else None,
                    )
                    
                    if 'created_at' in row.keys() and row['created_at']:
                        try:
                            # Handle different timestamp formats from sqlite string
                            if isinstance(row['created_at'], str):
                                job.created_at = datetime.fromisoformat(row['created_at'].split('.')[0])
                        except Exception:
                            pass
                            
                    db.add(job)
            db.commit()
            print("✅ Jobs migrated")
        except Exception as e:
            print("⚠️ Jobs migration failed:", e)
            
        conn.close()
        
    print("✅ Migration Complete!")

if __name__ == "__main__":
    migrate()
