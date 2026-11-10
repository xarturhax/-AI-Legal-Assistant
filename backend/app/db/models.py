from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    auth_version = db.Column(db.Integer, default=1, nullable=False)

    def get_id(self):
        return f"{self.id}:{self.auth_version}"


class Profile(db.Model):
    __tablename__ = "profiles"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name = db.Column(db.String(120), default="", nullable=False)
    details = db.Column(db.JSON, default=dict, nullable=False)
    settings = db.Column(
        db.JSON, default=lambda: {"mode": "baseline", "timezone": "Europe/Minsk"}, nullable=False
    )


class QueryHistory(db.Model):
    __tablename__ = "query_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_system = db.Column(db.String(20), default="ostis", nullable=False)
    source_id = db.Column(db.String(220), nullable=False)
    title = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "source_system", "source_id"),)


class Note(db.Model):
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id = db.Column(db.String(220))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False)
    timezone = db.Column(db.String(80), default="Europe/Minsk", nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class VerificationToken(db.Model):
    __tablename__ = "account_verification_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    purpose = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)


class ForumTopic(db.Model):
    __tablename__ = "forum_topics"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    tag_keys = db.Column(db.String(200), default="", nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)


class ForumPost(db.Model):
    __tablename__ = "forum_posts"
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(
        db.Integer, db.ForeignKey("forum_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    deleted_at = db.Column(db.DateTime)


class PostVote(db.Model):
    __tablename__ = "post_votes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(
        db.Integer, db.ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False
    )
    vote = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id"),
        db.CheckConstraint("vote IN (-1,1)"),
    )


class NewsCache(db.Model):
    __tablename__ = "news_cache"
    id = db.Column(db.Integer, primary_key=True)
    source_url = db.Column(db.String(2000), nullable=False)
    link = db.Column(db.String(2000), unique=True, nullable=False)
    title = db.Column(db.String(500), nullable=False)
    published_at = db.Column(db.String(100))
    excerpt = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, default=now, nullable=False)


class NewsFeedState(db.Model):
    __tablename__ = "news_feed_states"
    source_url = db.Column(db.String(2000), primary_key=True)
    checked_at = db.Column(db.DateTime, nullable=False, default=now)
    succeeded_at = db.Column(db.DateTime)
    error = db.Column(db.String(200))


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    round_id = db.Column(db.String(36), nullable=False)
    question_id = db.Column(db.String(220), nullable=False)
    answer_id = db.Column(db.String(220), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "round_id", "question_id"),)


class TopicView(db.Model):
    __tablename__ = "topic_views"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic_id = db.Column(
        db.Integer, db.ForeignKey("forum_topics.id", ondelete="CASCADE"), primary_key=True
    )
    viewed_at = db.Column(db.DateTime, default=now, nullable=False)


class RecommendationFeedback(db.Model):
    __tablename__ = "recommendation_feedback"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context = db.Column(db.String(40), nullable=False)
    topic_id = db.Column(
        db.Integer, db.ForeignKey("forum_topics.id", ondelete="CASCADE"), nullable=False
    )
    useful = db.Column(db.Boolean, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "context", "topic_id"),)
