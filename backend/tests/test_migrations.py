import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text


def test_existing_inventory_survives_upgrade_and_downgrade(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    env = {**os.environ, 'DATABASE_URL': url}
    def migrate(*args):
        subprocess.run([sys.executable, '-m', 'alembic', *args], env=env,
                       cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
    migrate('upgrade', '0001')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO items (name, quantity) VALUES ('Existing rice', 2.5)"))
    migrate('upgrade', 'head')
    with engine.connect() as db:
        row = db.execute(text('SELECT item_name, amount, balance FROM movements')).one()
        assert tuple(row) == ('Existing rice', 2.5, 2.5)
    migrate('downgrade', '0001')
    with engine.connect() as db:
        assert db.scalar(text('SELECT quantity FROM items')) == 2.5
    migrate('upgrade', 'head')
    engine.dispose()
