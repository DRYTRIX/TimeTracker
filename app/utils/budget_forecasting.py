"""
Budget Forecasting Utility

This module provides functions for calculating burn rates, forecasting completion dates,
analyzing resource allocation, and performing cost trend analysis for projects.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from app import db
from app.models import Project, TimeEntry, ProjectCost, User
from collections import defaultdict
import statistics


def calculate_burn_rate(project_id: int, days: int = 30) -> Dict:
    """
    Calculate the burn rate for a project based on recent activity.
    
    Args:
        project_id: ID of the project
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with burn rate metrics:
        - daily_burn_rate: Average daily cost
        - weekly_burn_rate: Average weekly cost
        - monthly_burn_rate: Average monthly cost
        - period_total: Total consumed in the period
        - period_days: Number of days in the period
    """
    project = Project.query.get(project_id)
    if not project:
        return None
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Calculate time-based costs
    time_entries = TimeEntry.query.filter(
        TimeEntry.project_id == project_id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.billable == True,
        func.date(TimeEntry.start_time) >= start_date,
        func.date(TimeEntry.start_time) <= end_date
    ).all()
    
    time_cost = Decimal('0')
    hourly_rate = project.hourly_rate or Decimal('0')
    
    for entry in time_entries:
        hours = Decimal(str(entry.duration_seconds / 3600))
        time_cost += hours * hourly_rate
    
    # Calculate direct costs
    direct_costs = ProjectCost.get_total_costs(
        project_id,
        start_date=start_date,
        end_date=end_date,
        billable_only=True
    )
    
    total_cost = float(time_cost) + direct_costs
    
    # Calculate rates
    daily_burn_rate = total_cost / days if days > 0 else 0
    weekly_burn_rate = daily_burn_rate * 7
    monthly_burn_rate = daily_burn_rate * 30
    
    return {
        'daily_burn_rate': round(daily_burn_rate, 2),
        'weekly_burn_rate': round(weekly_burn_rate, 2),
        'monthly_burn_rate': round(monthly_burn_rate, 2),
        'period_total': round(total_cost, 2),
        'period_days': days,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }


def estimate_completion_date(project_id: int, analysis_days: int = 30) -> Dict:
    """
    Estimate project completion date based on burn rate and remaining budget.
    
    Args:
        project_id: ID of the project
        analysis_days: Number of days to analyze for burn rate (default: 30)
    
    Returns:
        Dictionary with completion estimates:
        - estimated_completion_date: Estimated date when budget will be exhausted
        - days_remaining: Number of days until budget exhaustion
        - budget_amount: Total project budget
        - consumed_amount: Amount consumed so far
        - remaining_budget: Amount remaining
        - daily_burn_rate: Current daily burn rate
        - confidence: Confidence level ('high', 'medium', 'low')
    """
    project = Project.query.get(project_id)
    if not project or not project.budget_amount:
        return None
    
    burn_rate = calculate_burn_rate(project_id, analysis_days)
    if not burn_rate or burn_rate['daily_burn_rate'] == 0:
        return {
            'estimated_completion_date': None,
            'days_remaining': None,
            'budget_amount': float(project.budget_amount),
            'consumed_amount': project.budget_consumed_amount,
            'remaining_budget': float(project.budget_amount) - project.budget_consumed_amount,
            'daily_burn_rate': 0,
            'confidence': 'low',
            'message': 'No recent activity to estimate completion date'
        }
    
    budget_amount = float(project.budget_amount)
    consumed_amount = project.budget_consumed_amount
    remaining_budget = budget_amount - consumed_amount
    
    daily_burn = burn_rate['daily_burn_rate']
    
    if remaining_budget <= 0:
        return {
            'estimated_completion_date': datetime.now().date().isoformat(),
            'days_remaining': 0,
            'budget_amount': budget_amount,
            'consumed_amount': consumed_amount,
            'remaining_budget': remaining_budget,
            'daily_burn_rate': daily_burn,
            'confidence': 'high',
            'message': 'Budget already exhausted'
        }
    
    days_remaining = int(remaining_budget / daily_burn) if daily_burn > 0 else 999999
    estimated_date = datetime.now().date() + timedelta(days=days_remaining)
    
    # Calculate confidence based on data consistency
    confidence = _calculate_confidence(project_id, analysis_days)
    
    return {
        'estimated_completion_date': estimated_date.isoformat(),
        'days_remaining': days_remaining,
        'budget_amount': budget_amount,
        'consumed_amount': round(consumed_amount, 2),
        'remaining_budget': round(remaining_budget, 2),
        'daily_burn_rate': daily_burn,
        'confidence': confidence,
        'message': f'Based on {analysis_days} days of activity'
    }


def analyze_resource_allocation(project_id: int, days: int = 30) -> Dict:
    """
    Analyze resource allocation and costs per team member.
    
    Args:
        project_id: ID of the project
        days: Number of days to analyze (default: 30)
    
    Returns:
        Dictionary with resource allocation data:
        - users: List of users with their hours and costs
        - total_hours: Total hours across all users
        - total_cost: Total cost across all users
        - cost_distribution: Percentage breakdown by user
    """
    project = Project.query.get(project_id)
    if not project:
        return None
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Query time entries by user
    user_data = db.session.query(
        User.id,
        User.username,
        User.full_name,
        func.sum(TimeEntry.duration_seconds).label('total_seconds'),
        func.count(TimeEntry.id).label('entry_count')
    ).join(TimeEntry).filter(
        TimeEntry.project_id == project_id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.billable == True,
        func.date(TimeEntry.start_time) >= start_date,
        func.date(TimeEntry.start_time) <= end_date
    ).group_by(User.id, User.username, User.full_name).all()
    
    users = []
    total_hours = 0
    total_cost = 0
    
    hourly_rate = float(project.hourly_rate or 0)
    
    for user_id, username, full_name, total_seconds, entry_count in user_data:
        hours = total_seconds / 3600
        cost = hours * hourly_rate
        total_hours += hours
        total_cost += cost
        
        users.append({
            'user_id': user_id,
            'username': full_name if full_name else username,
            'hours': round(hours, 2),
            'cost': round(cost, 2),
            'entry_count': entry_count,
            'average_hours_per_entry': round(hours / entry_count, 2) if entry_count > 0 else 0
        })
    
    # Calculate cost distribution percentages
    for user in users:
        user['cost_percentage'] = round((user['cost'] / total_cost * 100), 1) if total_cost > 0 else 0
        user['hours_percentage'] = round((user['hours'] / total_hours * 100), 1) if total_hours > 0 else 0
    
    # Sort by cost (highest first)
    users.sort(key=lambda x: x['cost'], reverse=True)
    
    return {
        'users': users,
        'total_hours': round(total_hours, 2),
        'total_cost': round(total_cost, 2),
        'period_days': days,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'hourly_rate': hourly_rate
    }


def analyze_cost_trends(project_id: int, days: int = 90, granularity: str = 'week') -> Dict:
    """
    Analyze cost trends over time for a project.
    
    Args:
        project_id: ID of the project
        days: Number of days to analyze (default: 90)
        granularity: 'day', 'week', or 'month' (default: 'week')
    
    Returns:
        Dictionary with trend data:
        - periods: List of time periods with costs
        - trend_direction: 'increasing', 'decreasing', 'stable'
        - average_cost_per_period: Average cost per period
        - trend_percentage: Percentage change from first to last period
    """
    project = Project.query.get(project_id)
    if not project:
        return None
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get all time entries
    time_entries = TimeEntry.query.filter(
        TimeEntry.project_id == project_id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.billable == True,
        func.date(TimeEntry.start_time) >= start_date,
        func.date(TimeEntry.start_time) <= end_date
    ).all()
    
    # Get all project costs
    project_costs = ProjectCost.query.filter(
        ProjectCost.project_id == project_id,
        ProjectCost.billable == True,
        ProjectCost.cost_date >= start_date,
        ProjectCost.cost_date <= end_date
    ).all()
    
    hourly_rate = float(project.hourly_rate or 0)
    
    # Group by period
    period_costs = defaultdict(float)
    
    for entry in time_entries:
        period_key = _get_period_key(entry.start_time.date(), granularity)
        hours = entry.duration_seconds / 3600
        cost = hours * hourly_rate
        period_costs[period_key] += cost
    
    for cost in project_costs:
        period_key = _get_period_key(cost.cost_date, granularity)
        period_costs[period_key] += float(cost.amount)
    
    # Sort periods chronologically
    sorted_periods = sorted(period_costs.items())
    
    periods = [
        {
            'period': period,
            'cost': round(cost, 2)
        }
        for period, cost in sorted_periods
    ]
    
    # Calculate trend metrics
    if len(periods) >= 2:
        first_cost = periods[0]['cost']
        last_cost = periods[-1]['cost']
        
        if first_cost > 0:
            trend_percentage = ((last_cost - first_cost) / first_cost) * 100
        else:
            trend_percentage = 0
        
        # Determine trend direction
        costs_list = [p['cost'] for p in periods]
        avg_first_half = statistics.mean(costs_list[:len(costs_list)//2]) if len(costs_list) >= 2 else 0
        avg_second_half = statistics.mean(costs_list[len(costs_list)//2:]) if len(costs_list) >= 2 else 0
        
        if avg_second_half > avg_first_half * 1.1:
            trend_direction = 'increasing'
        elif avg_second_half < avg_first_half * 0.9:
            trend_direction = 'decreasing'
        else:
            trend_direction = 'stable'
    else:
        trend_percentage = 0
        trend_direction = 'insufficient_data'
    
    average_cost = statistics.mean([p['cost'] for p in periods]) if periods else 0
    
    return {
        'periods': periods,
        'trend_direction': trend_direction,
        'average_cost_per_period': round(average_cost, 2),
        'trend_percentage': round(trend_percentage, 1),
        'granularity': granularity,
        'period_count': len(periods),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }


def get_budget_status(project_id: int) -> Dict:
    """
    Get comprehensive budget status for a project.
    
    Args:
        project_id: ID of the project
    
    Returns:
        Dictionary with budget status:
        - budget_amount: Total budget
        - consumed_amount: Amount consumed
        - remaining_amount: Amount remaining
        - consumed_percentage: Percentage consumed
        - status: 'healthy', 'warning', 'critical', 'over_budget'
        - threshold_percent: Budget threshold setting
    """
    project = Project.query.get(project_id)
    if not project or not project.budget_amount:
        return None
    
    budget_amount = float(project.budget_amount)
    consumed_amount = project.budget_consumed_amount
    remaining_amount = budget_amount - consumed_amount
    consumed_percentage = (consumed_amount / budget_amount * 100) if budget_amount > 0 else 0
    
    threshold_percent = project.budget_threshold_percent or 80
    
    # Determine status
    if consumed_percentage >= 100:
        status = 'over_budget'
    elif consumed_percentage >= threshold_percent:
        status = 'critical'
    elif consumed_percentage >= threshold_percent * 0.75:
        status = 'warning'
    else:
        status = 'healthy'
    
    return {
        'budget_amount': budget_amount,
        'consumed_amount': round(consumed_amount, 2),
        'remaining_amount': round(remaining_amount, 2),
        'consumed_percentage': round(consumed_percentage, 1),
        'status': status,
        'threshold_percent': threshold_percent,
        'project_name': project.name,
        'project_id': project_id
    }


def _get_period_key(date_obj: date, granularity: str) -> str:
    """Get period key based on granularity."""
    if granularity == 'day':
        return date_obj.isoformat()
    elif granularity == 'week':
        # Get ISO week number
        year, week, _ = date_obj.isocalendar()
        return f"{year}-W{week:02d}"
    elif granularity == 'month':
        return f"{date_obj.year}-{date_obj.month:02d}"
    else:
        return date_obj.isoformat()


def _calculate_confidence(project_id: int, days: int) -> str:
    """
    Calculate confidence level for predictions based on data consistency.
    
    Returns:
        'high', 'medium', or 'low'
    """
    # Get daily costs for the period
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    project = Project.query.get(project_id)
    hourly_rate = float(project.hourly_rate or 0)
    
    # Group by day
    daily_costs = defaultdict(float)
    
    time_entries = TimeEntry.query.filter(
        TimeEntry.project_id == project_id,
        TimeEntry.end_time.isnot(None),
        TimeEntry.billable == True,
        func.date(TimeEntry.start_time) >= start_date,
        func.date(TimeEntry.start_time) <= end_date
    ).all()
    
    for entry in time_entries:
        day = entry.start_time.date()
        hours = entry.duration_seconds / 3600
        daily_costs[day] += hours * hourly_rate
    
    if len(daily_costs) < 7:
        return 'low'
    
    costs_list = list(daily_costs.values())
    
    if len(costs_list) < 2:
        return 'low'
    
    # Calculate coefficient of variation
    mean_cost = statistics.mean(costs_list)
    if mean_cost == 0:
        return 'low'
    
    std_dev = statistics.stdev(costs_list) if len(costs_list) > 1 else 0
    cv = std_dev / mean_cost
    
    # Lower CV means more consistent data, higher confidence
    if cv < 0.5:
        return 'high'
    elif cv < 1.0:
        return 'medium'
    else:
        return 'low'


def check_budget_alerts(project_id: int) -> List[Dict]:
    """
    Check if budget alerts should be triggered for a project.
    
    Args:
        project_id: ID of the project
    
    Returns:
        List of alerts that should be triggered
    """
    from app.models import BudgetAlert
    
    project = Project.query.get(project_id)
    if not project or not project.budget_amount:
        return []
    
    budget_status = get_budget_status(project_id)
    if not budget_status:
        return []
    
    alerts = []
    consumed_percentage = budget_status['consumed_percentage']
    threshold_percent = budget_status['threshold_percent']
    
    # Check for 80% threshold (or custom threshold)
    if consumed_percentage >= threshold_percent and consumed_percentage < 100:
        # Check if we already have a recent unacknowledged alert
        recent_alert = BudgetAlert.query.filter_by(
            project_id=project_id,
            alert_type='warning_80',
            is_acknowledged=False
        ).filter(
            BudgetAlert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if not recent_alert:
            alerts.append({
                'type': 'warning_80',
                'project_id': project_id,
                'budget_consumed_percent': consumed_percentage,
                'budget_amount': budget_status['budget_amount'],
                'consumed_amount': budget_status['consumed_amount']
            })
    
    # Check for 100% budget reached
    if consumed_percentage >= 100 and consumed_percentage < 105:
        recent_alert = BudgetAlert.query.filter_by(
            project_id=project_id,
            alert_type='warning_100',
            is_acknowledged=False
        ).filter(
            BudgetAlert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if not recent_alert:
            alerts.append({
                'type': 'warning_100',
                'project_id': project_id,
                'budget_consumed_percent': consumed_percentage,
                'budget_amount': budget_status['budget_amount'],
                'consumed_amount': budget_status['consumed_amount']
            })
    
    # Check for over budget
    if consumed_percentage >= 105:
        recent_alert = BudgetAlert.query.filter_by(
            project_id=project_id,
            alert_type='over_budget',
            is_acknowledged=False
        ).filter(
            BudgetAlert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if not recent_alert:
            alerts.append({
                'type': 'over_budget',
                'project_id': project_id,
                'budget_consumed_percent': consumed_percentage,
                'budget_amount': budget_status['budget_amount'],
                'consumed_amount': budget_status['consumed_amount']
            })
    
    return alerts

