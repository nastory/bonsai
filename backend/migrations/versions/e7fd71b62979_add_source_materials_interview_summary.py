"""add source_materials.interview_summary

Revision ID: e7fd71b62979
Revises: 9cac6fd7dd41
Create Date: 2026-08-03 08:19:32.043305

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7fd71b62979'
down_revision = '9cac6fd7dd41'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('source_materials', schema=None) as batch_op:
        batch_op.add_column(sa.Column('interview_summary', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('source_materials', schema=None) as batch_op:
        batch_op.drop_column('interview_summary')
