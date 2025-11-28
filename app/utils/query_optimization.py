"""
Database query optimization utilities.
Helps identify and fix N+1 query problems.
"""

from typing import List, Type, Optional
from sqlalchemy.orm import Query, joinedload, selectinload, subqueryload
from sqlalchemy import inspect
from app import db


def eager_load_relations(query: Query, model_class: Type, relations: List[str], strategy: str = "joined") -> Query:
    """
    Eagerly load relations to prevent N+1 queries.

    Args:
        query: SQLAlchemy query
        model_class: Model class
        relations: List of relation names to load
        strategy: Loading strategy ('joined', 'selectin', 'subquery')

    Returns:
        Query with eager loading options
    """
    loader_map = {"joined": joinedload, "selectin": selectinload, "subquery": subqueryload}

    loader_func = loader_map.get(strategy, joinedload)

    for relation in relations:
        if hasattr(model_class, relation):
            query = query.options(loader_func(getattr(model_class, relation)))

    return query


def get_model_relations(model_class: Type) -> List[str]:
    """
    Get all relation names for a model.

    Args:
        model_class: SQLAlchemy model class

    Returns:
        List of relation attribute names
    """
    inspector = inspect(model_class)
    return [rel.key for rel in inspector.relationships]


def optimize_list_query(query: Query, model_class: Type, common_relations: Optional[List[str]] = None) -> Query:
    """
    Optimize a list query by eagerly loading common relations.

    Args:
        query: SQLAlchemy query
        model_class: Model class
        common_relations: Optional list of relations to always load

    Returns:
        Optimized query
    """
    if common_relations:
        return eager_load_relations(query, model_class, common_relations)

    # Auto-detect common relations (relationships that are likely to be accessed)
    all_relations = get_model_relations(model_class)

    # Common patterns: user, project, client, task, etc.
    common_patterns = ["user", "project", "client", "task", "assignee", "creator"]
    relations_to_load = [rel for rel in all_relations if any(pattern in rel.lower() for pattern in common_patterns)]

    if relations_to_load:
        return eager_load_relations(query, model_class, relations_to_load)

    return query


def batch_load_relations(items: List[Type], relation_name: str, model_class: Type) -> None:
    """
    Batch load a relation for a list of items (prevents N+1).

    Note: This is a helper for cases where eager loading wasn't possible.
    Prefer using eager_load_relations in the query instead.

    Args:
        items: List of model instances
        relation_name: Name of relation to load
        model_class: Model class
    """
    if not items:
        return

    # Get IDs
    ids = [item.id for item in items]

    # Load all related items in one query
    relation = getattr(model_class, relation_name)
    related_items = (
        db.session.query(relation.property.mapper.class_).filter(relation.property.mapper.class_.id.in_(ids)).all()
    )

    # This is a simplified example - in practice, you'd need to map them back


class QueryProfiler:
    """Helper class to profile and optimize queries"""

    @staticmethod
    def count_queries(func):
        """Decorator to count database queries in a function"""
        from functools import wraps
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @wraps(func)
        def wrapper(*args, **kwargs):
            queries = []

            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                queries.append(statement)

            event.listen(Engine, "before_cursor_execute", before_cursor_execute)

            try:
                result = func(*args, **kwargs)
                return result, len(queries)
            finally:
                event.remove(Engine, "before_cursor_execute", before_cursor_execute)

        return wrapper
