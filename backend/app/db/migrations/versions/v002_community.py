"""Форум, новости и личные результаты учебного тестирования."""

import sqlalchemy as sa
from alembic import op

revision = "002_community"
down_revision = "001_accounts"
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
        "forum_topics",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        created(),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "forum_posts",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column(
            "topic_id",
            sa.Integer,
            sa.ForeignKey("forum_topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text, nullable=False),
        created(),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("deleted_at", sa.DateTime),
    )
    op.create_index("ix_forum_posts_topic_id", "forum_posts", ["topic_id"])
    op.create_table(
        "post_votes",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column(
            "post_id",
            sa.Integer,
            sa.ForeignKey("forum_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vote", sa.Integer, nullable=False),
        sa.UniqueConstraint("user_id", "post_id"),
        sa.CheckConstraint("vote IN (-1,1)"),
    )
    op.create_table(
        "news_cache",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("link", sa.String(2000), unique=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("published_at", sa.String(100)),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("fetched_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "news_feed_states",
        sa.Column("source_url", sa.String(2000), primary_key=True),
        sa.Column("checked_at", sa.DateTime, nullable=False),
        sa.Column("succeeded_at", sa.DateTime),
        sa.Column("error", sa.String(200)),
    )
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer, primary_key=True),
        owner(),
        sa.Column("round_id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(220), nullable=False),
        sa.Column("answer_id", sa.String(220), nullable=False),
        sa.Column("correct", sa.Boolean, nullable=False),
        created(),
        sa.UniqueConstraint("user_id", "round_id", "question_id"),
    )


def downgrade():
    raise RuntimeError("Автоматическое удаление данных отключено. Используйте резервную копию.")
