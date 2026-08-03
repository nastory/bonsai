"""rename source_materials.file_path to text_path

Revision ID: 9cac6fd7dd41
Revises: 08d567a6683f
Create Date: 2026-08-02 21:47:53.382921

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cac6fd7dd41'
down_revision = '08d567a6683f'
branch_labels = None
depends_on = None


def upgrade():
    # A true rename (not add+drop): preserves any existing rows' values and
    # avoids needing a server_default for a NOT NULL column, since nothing
    # about the column's nullability or content actually changes.
    with op.batch_alter_table('source_materials', schema=None) as batch_op:
        batch_op.alter_column('file_path', new_column_name='text_path', existing_type=sa.String())


def downgrade():
    with op.batch_alter_table('source_materials', schema=None) as batch_op:
        batch_op.alter_column('text_path', new_column_name='file_path', existing_type=sa.String())
