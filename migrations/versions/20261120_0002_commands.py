"""add commands and system state

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "command",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("decision_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_command")),
        sa.UniqueConstraint("command_id", name="uq_command_command_id"),
    )
    op.create_index("ix_command_device_created", "command", ["device_id", "created_at"], unique=False)
    op.create_index("ix_command_status", "command", ["status"], unique=False)

    op.create_table(
        "system_state",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("emergency_stop", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_state")),
    )


def downgrade() -> None:
    op.drop_table("system_state")
    op.drop_index("ix_command_status", table_name="command")
    op.drop_index("ix_command_device_created", table_name="command")
    op.drop_table("command")
