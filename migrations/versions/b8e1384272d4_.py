"""empty message

Revision ID: b8e1384272d4
Revises: 3a2162fd58de
Create Date: 2016-04-03 11:51:34.024195

"""

# revision identifiers, used by Alembic.
revision = 'b8e1384272d4'
down_revision = '3a2162fd58de'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('modules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('abbreviation', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('group_roles', sa.Column('role', sa.String(length=20), nullable=False))
    op.drop_column('group_roles', 'id')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('group_roles', sa.Column('id', sa.VARCHAR(length=20), autoincrement=False, nullable=False))
    op.drop_column('group_roles', 'role')
    op.drop_table('modules')
    ### end Alembic commands ###
