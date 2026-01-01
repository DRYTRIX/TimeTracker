"""Fix roles and permissions sequences after bulk insert

Revision ID: 089_fix_role_perm_sequences
Revises: 088_salesman_splitting_reports
Create Date: 2025-12-05

This migration fixes the PostgreSQL sequence issue where roles and permissions
tables had explicit IDs inserted (1-5 for roles, 1-50 for permissions) but the
sequences were not updated, causing duplicate key errors when creating new records.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '089_fix_role_perm_sequences'
down_revision = '088_salesman_splitting_reports'
branch_labels = None
depends_on = None


def upgrade():
    """Fix sequences for roles and permissions tables"""
    connection = op.get_bind()
    is_postgresql = connection.dialect.name == 'postgresql'
    
    # SQLite doesn't use sequences - it uses AUTOINCREMENT which is automatically managed
    # This migration only applies to PostgreSQL
    if not is_postgresql:
        return
    
    # Fix roles sequence
    # Create sequence if it doesn't exist, link it to the table, then set it to max_id + 1
    connection.execute(sa.text("""
        DO $$
        BEGIN
            -- Create sequence if it doesn't exist
            CREATE SEQUENCE IF NOT EXISTS roles_id_seq;
            
            -- Link sequence to table column if not already linked
            IF NOT EXISTS (
                SELECT 1 FROM pg_depend 
                WHERE objid = 'roles_id_seq'::regclass 
                AND refobjid = 'roles'::regclass
            ) THEN
                ALTER TABLE roles ALTER COLUMN id SET DEFAULT nextval('roles_id_seq');
                ALTER SEQUENCE roles_id_seq OWNED BY roles.id;
            END IF;
            
            -- Set sequence to max(id) + 1
            PERFORM setval('roles_id_seq', 
                COALESCE((SELECT MAX(id) FROM roles), 0) + 1, 
                false);
        END $$;
    """))
    
    # Fix permissions sequence
    # Create sequence if it doesn't exist, link it to the table, then set it to max_id + 1
    connection.execute(sa.text("""
        DO $$
        BEGIN
            -- Create sequence if it doesn't exist
            CREATE SEQUENCE IF NOT EXISTS permissions_id_seq;
            
            -- Link sequence to table column if not already linked
            IF NOT EXISTS (
                SELECT 1 FROM pg_depend 
                WHERE objid = 'permissions_id_seq'::regclass 
                AND refobjid = 'permissions'::regclass
            ) THEN
                ALTER TABLE permissions ALTER COLUMN id SET DEFAULT nextval('permissions_id_seq');
                ALTER SEQUENCE permissions_id_seq OWNED BY permissions.id;
            END IF;
            
            -- Set sequence to max(id) + 1
            PERFORM setval('permissions_id_seq', 
                COALESCE((SELECT MAX(id) FROM permissions), 0) + 1, 
                false);
        END $$;
    """))


def downgrade():
    """No downgrade needed - sequences will be automatically managed"""
    pass

