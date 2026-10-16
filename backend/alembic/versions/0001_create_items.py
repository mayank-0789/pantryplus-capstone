"""create items table

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False, server_default="other"),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=8), nullable=False, server_default="pcs"),
        sa.Column("min_quantity", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_items_category", "items", ["category"])
    op.create_index("ix_items_expires_on", "items", ["expires_on"])


def downgrade() -> None:
    op.drop_index("ix_items_expires_on", table_name="items")
    op.drop_index("ix_items_category", table_name="items")
    op.drop_table("items")
