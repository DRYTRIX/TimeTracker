"""
Service for data import operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import csv
from io import TextIOWrapper
from app.services import TimeTrackingService, ProjectService, ClientService
from app.repositories import ProjectRepository, ClientRepository
from app.models import Project, Client


class ImportService:
    """Service for import operations"""
    
    def __init__(self):
        self.time_tracking_service = TimeTrackingService()
        self.project_service = ProjectService()
        self.client_service = ClientService()
        self.project_repo = ProjectRepository()
        self.client_repo = ClientRepository()
    
    def import_time_entries_csv(
        self,
        file,
        user_id: int,
        default_project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Import time entries from CSV.
        
        CSV format expected:
        Date, Project, Start Time, End Time, Notes, Tags, Billable
        
        Returns:
            dict with 'success', 'imported', 'errors' keys
        """
        imported = 0
        errors = []
        
        try:
            # Parse CSV
            reader = csv.DictReader(TextIOWrapper(file, encoding='utf-8'))
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Parse date
                    date_str = row.get('Date', '').strip()
                    if not date_str:
                        errors.append(f"Row {row_num}: Missing date")
                        continue
                    
                    # Parse project
                    project_name = row.get('Project', '').strip()
                    project_id = default_project_id
                    
                    if project_name and not project_id:
                        # Find or create project
                        project = self.project_repo.find_one_by(name=project_name)
                        if not project:
                            errors.append(f"Row {row_num}: Project '{project_name}' not found")
                            continue
                        project_id = project.id
                    
                    if not project_id:
                        errors.append(f"Row {row_num}: No project specified")
                        continue
                    
                    # Parse times
                    start_time_str = row.get('Start Time', '').strip()
                    end_time_str = row.get('End Time', '').strip()
                    
                    if not start_time_str or not end_time_str:
                        errors.append(f"Row {row_num}: Missing start or end time")
                        continue
                    
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid time format")
                        continue
                    
                    # Create entry
                    result = self.time_tracking_service.create_manual_entry(
                        user_id=user_id,
                        project_id=project_id,
                        start_time=start_time,
                        end_time=end_time,
                        notes=row.get('Notes', '').strip() or None,
                        tags=row.get('Tags', '').strip() or None,
                        billable=row.get('Billable', 'Yes').strip().lower() == 'yes'
                    )
                    
                    if result['success']:
                        imported += 1
                    else:
                        errors.append(f"Row {row_num}: {result['message']}")
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return {
                'success': True,
                'imported': imported,
                'errors': errors,
                'total_rows': imported + len(errors)
            }
        
        except Exception as e:
            return {
                'success': False,
                'imported': imported,
                'errors': [f"Import failed: {str(e)}"],
                'total_rows': 0
            }
    
    def import_projects_csv(
        self,
        file,
        created_by: int
    ) -> Dict[str, Any]:
        """
        Import projects from CSV.
        
        CSV format expected:
        Name, Client, Description, Billable, Hourly Rate
        
        Returns:
            dict with 'success', 'imported', 'errors' keys
        """
        imported = 0
        errors = []
        
        try:
            reader = csv.DictReader(TextIOWrapper(file, encoding='utf-8'))
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    name = row.get('Name', '').strip()
                    if not name:
                        errors.append(f"Row {row_num}: Missing project name")
                        continue
                    
                    client_name = row.get('Client', '').strip()
                    if not client_name:
                        errors.append(f"Row {row_num}: Missing client name")
                        continue
                    
                    # Find or create client
                    client = self.client_repo.get_by_name(client_name)
                    if not client:
                        # Create client
                        client_result = self.client_service.create_client(
                            name=client_name,
                            created_by=created_by
                        )
                        if not client_result['success']:
                            errors.append(f"Row {row_num}: Could not create client: {client_result['message']}")
                            continue
                        client = client_result['client']
                    
                    # Create project
                    result = self.project_service.create_project(
                        name=name,
                        client_id=client.id,
                        description=row.get('Description', '').strip() or None,
                        billable=row.get('Billable', 'Yes').strip().lower() == 'yes',
                        hourly_rate=Decimal(row.get('Hourly Rate', '0')) if row.get('Hourly Rate') else None,
                        created_by=created_by
                    )
                    
                    if result['success']:
                        imported += 1
                    else:
                        errors.append(f"Row {row_num}: {result['message']}")
                
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return {
                'success': True,
                'imported': imported,
                'errors': errors,
                'total_rows': imported + len(errors)
            }
        
        except Exception as e:
            return {
                'success': False,
                'imported': imported,
                'errors': [f"Import failed: {str(e)}"],
                'total_rows': 0
            }

