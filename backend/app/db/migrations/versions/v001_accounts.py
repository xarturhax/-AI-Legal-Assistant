"""Начальная схема аккаунтов и личных данных; правовых текстов в ней нет."""

import sqlalchemy as sa
from alembic import op

revision = "001_accounts"
down_revision = None
branch_labels = None
depends_on = None


def owner():
    return sa.Column(
        "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


def created():
    return sa.Column("created_at", sa.DateTime, nullable=False)


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(254), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        created(),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_verified", sa.Boolean, nullable=False),
        sa.Column("auth_version", sa.Integer, nullable=False),
    )
    op.create_table(
        "profiles",
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("settings", sa.JSON, nullable=False),
    )
    op.create_table(
        "query_history",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        created(),
    )
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("source_system", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(220), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        created(),
        sa.UniqueConstraint("user_id", "source_system", "source_id"),
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("source_id", sa.String(220)),
        sa.Column("text", sa.Text, nullable=False),
        created(),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("starts_at", sa.DateTime, nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        created(),
    )
    op.create_table(
        "account_verification_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime),
    )
    for table in (
        "query_history",
        "bookmarks",
        "notes",
        "calendar_events",
        "account_verification_tokens",
    ):
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade():
    raise RuntimeError(
        "Автоматическое удаление пользовательских таблиц отключено; используйте бэкап."
    )
