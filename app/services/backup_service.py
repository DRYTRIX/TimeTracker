"""
Service for backup operations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import shutil
from pathlib import Path
from flask import current_app
from app import db
from sqlalchemy import text


class BackupService:
    """Service for backup operations"""
    
    def __init__(self):
        self.backup_dir = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', '/data'),
            'backups'
        )
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_database_backup(
        self,
        backup_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a database backup.
        
        Returns:
            dict with 'success', 'message', and 'backup_path' keys
        """
        try:
            # Generate backup filename
            if not backup_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"timetracker_backup_{timestamp}.sql"
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Get database URL
            db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            # PostgreSQL backup using pg_dump
            if 'postgresql' in db_url:
                import subprocess
                from urllib.parse import urlparse
                
                parsed = urlparse(db_url.replace('postgresql+psycopg2://', 'postgresql://'))
                
                cmd = [
                    'pg_dump',
                    '-h', parsed.hostname or 'localhost',
                    '-p', str(parsed.port or 5432),
                    '-U', parsed.username or 'timetracker',
                    '-d', parsed.path.lstrip('/') or 'timetracker',
                    '-f', backup_path,
                    '--no-password'  # Use .pgpass file
                ]
                
                # Set password via environment
                env = os.environ.copy()
                if parsed.password:
                    env['PGPASSWORD'] = parsed.password
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'message': f'Backup failed: {result.stderr}',
                        'error': 'backup_failed'
                    }
            
            # SQLite backup
            elif 'sqlite' in db_url:
                db_path = db_url.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path)
            
            else:
                return {
                    'success': False,
                    'message': 'Unsupported database type',
                    'error': 'unsupported_db'
                }
            
            # Get backup size
            backup_size = os.path.getsize(backup_path)
            
            return {
                'success': True,
                'message': 'Backup created successfully',
                'backup_path': backup_path,
                'backup_size': backup_size,
                'backup_name': backup_name
            }
        
        except Exception as e:
            current_app.logger.error(f"Backup failed: {e}")
            return {
                'success': False,
                'message': f'Backup failed: {str(e)}',
                'error': 'backup_error'
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup information dicts
        """
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.sql') or filename.endswith('.db'):
                filepath = os.path.join(self.backup_dir, filename)
                stat = os.stat(filepath)
                
                backups.append({
                    'name': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """
        Delete a backup file.
        
        Returns:
            dict with 'success' and 'message' keys
        """
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'message': 'Backup not found',
                'error': 'not_found'
            }
        
        try:
            os.remove(backup_path)
            return {
                'success': True,
                'message': 'Backup deleted successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to delete backup: {str(e)}',
                'error': 'delete_error'
            }

