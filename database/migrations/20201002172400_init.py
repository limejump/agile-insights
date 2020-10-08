"""
Initial Migration
"""

name = "20201002172400_init"
dependencies = []


def upgrade(db):
    db.teams.insert_many([
        {"name": "cx"},
        {"name": "voyager"},
        {"name": "dar"},
        {"name": "platform"},
        {"name": "infra"},
        {"name": "embedded"},
        {"name": "helios"}
    ])


def downgrade(db):
    db.teams.drop()
