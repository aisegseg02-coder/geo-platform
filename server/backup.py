"""
Backup System - Automated Database Backups with Cloud Storage
"""
import os
import shutil
import sqlite3
import json
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import subprocess

OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', './output'))
BACKUP_DIR = OUTPUT_DIR / 'backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Database files to backup
DB_FILES = [
    OUTPUT_DIR / 'jobs.db',
    OUTPUT_DIR / 'users.db',
    OUTPUT_DIR / 'security.db',
    OUTPUT_DIR / 'competitor_cache.db',
    OUTPUT_DIR / 'result_cache.db'
]

# ── Backup Functions ────────────────────────────────────────────────────────

def create_backup(compress: bool = True) -> dict:
    """Create full backup of all databases and important files"""
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    backup_path.mkdir(exist_ok=True)
    
    backed_up = []
    errors = []
    
    # Backup databases
    for db_file in DB_FILES:
        if db_file.exists():
            try:
                dest = backup_path / db_file.name
                shutil.copy2(db_file, dest)
                backed_up.append(str(db_file.name))
            except Exception as e:
                errors.append(f"{db_file.name}: {str(e)}")
    
    # Backup important JSON files
    json_files = [
        'audit.json', 'analysis.json', 'history.json', 
        'recommendations.json', 'settings.json'
    ]
    
    for json_file in json_files:
        src = OUTPUT_DIR / json_file
        if src.exists():
            try:
                dest = backup_path / json_file
                shutil.copy2(src, dest)
                backed_up.append(json_file)
            except Exception as e:
                errors.append(f"{json_file}: {str(e)}")
    
    # Create backup manifest
    manifest = {
        'timestamp': timestamp,
        'created_at': datetime.utcnow().isoformat(),
        'files': backed_up,
        'errors': errors,
        'compressed': False
    }
    
    manifest_path = backup_path / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Compress if requested
    if compress:
        try:
            archive_path = BACKUP_DIR / f"{backup_name}.tar.gz"
            shutil.make_archive(str(backup_path), 'gztar', backup_path)
            shutil.rmtree(backup_path)
            manifest['compressed'] = True
            manifest['archive_path'] = str(archive_path) + '.tar.gz'
            manifest['size_mb'] = round(Path(str(archive_path) + '.tar.gz').stat().st_size / 1024 / 1024, 2)
        except Exception as e:
            errors.append(f"Compression failed: {str(e)}")
    
    return manifest

def list_backups() -> list:
    """List all available backups"""
    backups = []
    
    # List compressed backups
    for archive in BACKUP_DIR.glob('backup_*.tar.gz'):
        try:
            stat = archive.stat()
            backups.append({
                'name': archive.stem,
                'path': str(archive),
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'compressed': True
            })
        except Exception:
            pass
    
    # List uncompressed backups
    for backup_dir in BACKUP_DIR.glob('backup_*'):
        if backup_dir.is_dir():
            manifest_path = backup_dir / 'manifest.json'
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    backups.append({
                        'name': backup_dir.name,
                        'path': str(backup_dir),
                        'created_at': manifest.get('created_at'),
                        'files': manifest.get('files', []),
                        'compressed': False
                    })
                except Exception:
                    pass
    
    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return backups

def restore_backup(backup_name: str) -> dict:
    """Restore from backup"""
    backup_path = BACKUP_DIR / backup_name
    archive_path = BACKUP_DIR / f"{backup_name}.tar.gz"
    
    restored = []
    errors = []
    
    # Extract if compressed
    if archive_path.exists():
        try:
            shutil.unpack_archive(archive_path, BACKUP_DIR)
            backup_path = BACKUP_DIR / backup_name
        except Exception as e:
            return {'success': False, 'error': f"Extract failed: {str(e)}"}
    
    if not backup_path.exists():
        return {'success': False, 'error': 'Backup not found'}
    
    # Read manifest
    manifest_path = backup_path / 'manifest.json'
    if not manifest_path.exists():
        return {'success': False, 'error': 'Invalid backup (no manifest)'}
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Restore databases
    for db_file in DB_FILES:
        src = backup_path / db_file.name
        if src.exists():
            try:
                # Backup current before overwriting
                if db_file.exists():
                    backup_current = db_file.with_suffix('.db.bak')
                    shutil.copy2(db_file, backup_current)
                
                shutil.copy2(src, db_file)
                restored.append(db_file.name)
            except Exception as e:
                errors.append(f"{db_file.name}: {str(e)}")
    
    # Restore JSON files
    for json_file in manifest.get('files', []):
        if json_file.endswith('.json'):
            src = backup_path / json_file
            dest = OUTPUT_DIR / json_file
            if src.exists():
                try:
                    shutil.copy2(src, dest)
                    restored.append(json_file)
                except Exception as e:
                    errors.append(f"{json_file}: {str(e)}")
    
    return {
        'success': len(errors) == 0,
        'restored': restored,
        'errors': errors,
        'backup_date': manifest.get('created_at')
    }

def delete_backup(backup_name: str) -> bool:
    """Delete a backup"""
    backup_path = BACKUP_DIR / backup_name
    archive_path = BACKUP_DIR / f"{backup_name}.tar.gz"
    
    try:
        if archive_path.exists():
            archive_path.unlink()
        if backup_path.exists() and backup_path.is_dir():
            shutil.rmtree(backup_path)
        return True
    except Exception:
        return False

def cleanup_old_backups(keep_days: int = 30):
    """Delete backups older than specified days"""
    cutoff = datetime.utcnow() - timedelta(days=keep_days)
    deleted = []
    
    for backup in list_backups():
        created_at = datetime.fromisoformat(backup['created_at'])
        if created_at < cutoff:
            if delete_backup(backup['name']):
                deleted.append(backup['name'])
    
    return deleted

# ── Cloud Backup (S3/GCS) ───────────────────────────────────────────────────

def upload_to_s3(backup_path: str, bucket: str, key: str) -> bool:
    """Upload backup to AWS S3"""
    try:
        import boto3
        s3 = boto3.client('s3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        s3.upload_file(backup_path, bucket, key)
        return True
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        return False

def upload_to_gcs(backup_path: str, bucket: str, blob_name: str) -> bool:
    """Upload backup to Google Cloud Storage"""
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(backup_path)
        return True
    except Exception as e:
        print(f"❌ GCS upload failed: {e}")
        return False

def backup_to_cloud(backup_name: str) -> dict:
    """Upload backup to configured cloud storage"""
    archive_path = BACKUP_DIR / f"{backup_name}.tar.gz"
    
    if not archive_path.exists():
        return {'success': False, 'error': 'Backup archive not found'}
    
    results = {}
    
    # Try S3
    s3_bucket = os.getenv('BACKUP_S3_BUCKET')
    if s3_bucket:
        key = f"geo-platform-backups/{backup_name}.tar.gz"
        results['s3'] = upload_to_s3(str(archive_path), s3_bucket, key)
    
    # Try GCS
    gcs_bucket = os.getenv('BACKUP_GCS_BUCKET')
    if gcs_bucket:
        blob_name = f"geo-platform-backups/{backup_name}.tar.gz"
        results['gcs'] = upload_to_gcs(str(archive_path), gcs_bucket, blob_name)
    
    return {
        'success': any(results.values()),
        'results': results
    }

# ── Scheduled Backup ────────────────────────────────────────────────────────

def schedule_daily_backup():
    """Schedule daily backup (call this from scheduler)"""
    try:
        manifest = create_backup(compress=True)
        
        # Upload to cloud if configured
        if manifest.get('compressed'):
            backup_name = Path(manifest['archive_path']).stem
            backup_to_cloud(backup_name)
        
        # Cleanup old backups
        cleanup_old_backups(keep_days=30)
        
        return {'success': True, 'manifest': manifest}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ── Export/Import Data ──────────────────────────────────────────────────────

def export_all_data() -> dict:
    """Export all data to JSON format"""
    export_data = {
        'exported_at': datetime.utcnow().isoformat(),
        'version': '1.0',
        'data': {}
    }
    
    # Export from each database
    for db_file in DB_FILES:
        if db_file.exists():
            try:
                conn = sqlite3.connect(str(db_file))
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                
                # Get all tables
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in c.fetchall()]
                
                db_data = {}
                for table in tables:
                    c.execute(f"SELECT * FROM {table}")
                    rows = [dict(row) for row in c.fetchall()]
                    db_data[table] = rows
                
                export_data['data'][db_file.stem] = db_data
                conn.close()
            except Exception as e:
                export_data['data'][db_file.stem] = {'error': str(e)}
    
    return export_data

def import_data(data: dict) -> dict:
    """Import data from JSON format"""
    imported = []
    errors = []
    
    for db_name, db_data in data.get('data', {}).items():
        db_file = OUTPUT_DIR / f"{db_name}.db"
        
        try:
            conn = sqlite3.connect(str(db_file))
            c = conn.cursor()
            
            for table, rows in db_data.items():
                if isinstance(rows, list) and rows:
                    # Get column names
                    columns = list(rows[0].keys())
                    placeholders = ','.join(['?' for _ in columns])
                    
                    # Insert rows
                    for row in rows:
                        values = [row.get(col) for col in columns]
                        c.execute(f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})", values)
            
            conn.commit()
            conn.close()
            imported.append(db_name)
        except Exception as e:
            errors.append(f"{db_name}: {str(e)}")
    
    return {
        'success': len(errors) == 0,
        'imported': imported,
        'errors': errors
    }

# ── Backup Status ───────────────────────────────────────────────────────────

def get_backup_status() -> dict:
    """Get backup system status"""
    backups = list_backups()
    
    total_size = sum(b.get('size_mb', 0) for b in backups)
    latest = backups[0] if backups else None
    
    return {
        'total_backups': len(backups),
        'total_size_mb': round(total_size, 2),
        'latest_backup': latest,
        'backup_dir': str(BACKUP_DIR),
        'cloud_configured': {
            's3': bool(os.getenv('BACKUP_S3_BUCKET')),
            'gcs': bool(os.getenv('BACKUP_GCS_BUCKET'))
        }
    }
