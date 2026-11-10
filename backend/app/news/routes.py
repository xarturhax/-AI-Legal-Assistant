from flask import Blueprint, render_template

from app.db.models import NewsCache, NewsFeedState
from app.extensions import db

bp = Blueprint("news", __name__)


@bp.get("/news")
def news():
    items = (
        db.session.execute(db.select(NewsCache).order_by(NewsCache.fetched_at.desc()).limit(100))
        .scalars()
        .all()
    )
    states = db.session.execute(db.select(NewsFeedState)).scalars().all()
    return render_template("news.html", items=items, states=states)
