"""add goal_type to goals

Revision ID: a1f2c3d4e5b6
Revises: 04b7766a0518
Create Date: 2026-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1f2c3d4e5b6'
down_revision = '04b7766a0518'
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows backfill to 'cap' (current semantics: rewarded for staying under threshold).
    with op.batch_alter_table('goals') as batch_op:
        batch_op.add_column(sa.Column('goal_type', sa.String(length=10),
                                       nullable=False, server_default='cap'))
    # Drop the server_default so future inserts must specify goal_type explicitly.
    with op.batch_alter_table('goals') as batch_op:
        batch_op.alter_column('goal_type', server_default=None)


def downgrade():
    with op.batch_alter_table('goals') as batch_op:
        batch_op.drop_column('goal_type')
