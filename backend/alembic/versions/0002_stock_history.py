"""Add persistent stock history and quantity constraints."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("items") as batch:
        batch.create_check_constraint("ck_items_quantity", "quantity >= 0 AND quantity <= 99999999.99")
        batch.create_check_constraint("ck_items_min_quantity", "min_quantity >= 0 AND min_quantity <= 99999999.99")
    op.create_table("movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_name", sa.String(80), nullable=False),
        sa.Column("unit", sa.String(8), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False),
        sa.Column("note", sa.String(200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_movements_item_id", "movements", ["item_id"])
    op.execute("INSERT INTO movements (item_id, item_name, unit, kind, amount, balance, note) "
               "SELECT id, name, unit, 'opening', quantity, quantity, 'Balance at migration' FROM items")


def downgrade():
    op.drop_table("movements")
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("ck_items_quantity", type_="check")
        batch.drop_constraint("ck_items_min_quantity", type_="check")
