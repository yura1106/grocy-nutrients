"""add currency rates table

Revision ID: 001
Revises:
Create Date: 2024-03-29 20:42:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'currency_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_currency', sa.String(), nullable=True),
        sa.Column('target_currency', sa.String(), nullable=True),
        sa.Column('rate', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_currency_rates_base_currency'), 'currency_rates', ['base_currency'], unique=False)
    op.create_index(op.f('ix_currency_rates_id'), 'currency_rates', ['id'], unique=False)
    op.create_index(op.f('ix_currency_rates_target_currency'), 'currency_rates', ['target_currency'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_currency_rates_target_currency'), table_name='currency_rates')
    op.drop_index(op.f('ix_currency_rates_id'), table_name='currency_rates')
    op.drop_index(op.f('ix_currency_rates_base_currency'), table_name='currency_rates')
    op.drop_table('currency_rates')
