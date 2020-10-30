"""
Add datascience
"""

name = "20201030143800_add_datascience"
dependencies = ["20201008172100_issue_name_index"]


def upgrade(db):
    db.teams.insert_one({"name": "datascience"})


def downgrade(db):
    db.teams.delete_one({'name': 'datascience'})
