from pathlib import Path

from alembic import command
from alembic.config import Config

from app.extensions import db


def upgrade():
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
