"""Add client notes table for internal notes about clients

Revision ID: 025
Revises: 024
Create Date: 2025-10-24 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create client_notes table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if client_notes table already exists
    if 'client_notes' not in inspector.get_table_names():
        op.create_table('client_notes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('is_important', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for better performance
        op.create_index('ix_client_notes_client_id', 'client_notes', ['client_id'], unique=False)
        op.create_index('ix_client_notes_user_id', 'client_notes', ['user_id'], unique=False)
        op.create_index('ix_client_notes_created_at', 'client_notes', ['created_at'], unique=False)
        op.create_index('ix_client_notes_is_important', 'client_notes', ['is_important'], unique=False)
        
        print("✓ Created client_notes table")
    else:
        print("ℹ client_notes table already exists")


def downgrade() -> None:
    """Drop client_notes table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if client_notes table exists before trying to drop it
    if 'client_notes' in inspector.get_table_names():
        try:
            # Drop indexes first
            op.drop_index('ix_client_notes_is_important', table_name='client_notes')
            op.drop_index('ix_client_notes_created_at', table_name='client_notes')
            op.drop_index('ix_client_notes_user_id', table_name='client_notes')
            op.drop_index('ix_client_notes_client_id', table_name='client_notes')
            
            # Drop the table
            op.drop_table('client_notes')
            print("✓ Dropped client_notes table")
        except Exception as e:
            print(f"⚠ Warning dropping client_notes table: {e}")
    else:
        print("ℹ client_notes table does not exist")

