"""
Make unique index on issue name for historic issues, so that
we don't end up with duplicates
"""

name = "20201008172100_issue_name_index"
# FIXME: This isn't really true, but if you don't list
# a dependency it bitches that you've specified to init migrations.
dependencies = ["20201002172400_init"]


def upgrade(db):
    db.historic_issues.create_index("name", unique=True)


def downgrade(db):
    db.historic_issues.drop_index("name")
