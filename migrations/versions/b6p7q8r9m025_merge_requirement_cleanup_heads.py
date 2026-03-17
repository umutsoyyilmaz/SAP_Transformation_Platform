"""Merge active migration heads before legacy requirement FK drop.

Revision ID: b6p7q8r9m025
Revises: 9i0j1k2l3m410, a5o6p7q8l924, b1c2d3e4f5a6
Create Date: 2026-03-10
"""


# revision identifiers, used by Alembic.
revision = "b6p7q8r9m025"
down_revision = ("9i0j1k2l3m410", "a5o6p7q8l924", "b1c2d3e4f5a6")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
