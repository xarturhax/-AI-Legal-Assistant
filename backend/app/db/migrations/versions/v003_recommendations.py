"""Просмотры, тематические метки и персональная обратная связь форума."""

import sqlalchemy as sa
from alembic import op

revision = "003_recommendations"
down_revision = "002_community"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "forum_topics", sa.Column("tag_keys", sa.String(200), server_default="", nullable=False)
    )
    op.create_table(
        "topic_views",
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "topic_id",
            sa.Integer,
            sa.ForeignKey("forum_topics.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("viewed_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("context", sa.String(40), nullable=False),
        sa.Column(
            "topic_id",
            sa.Integer,
            sa.ForeignKey("forum_topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("useful", sa.Boolean, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "context", "topic_id"),
    )


def downgrade():
    raise RuntimeError("Удаление истории просмотров отключено; используйте резервную копию.")
