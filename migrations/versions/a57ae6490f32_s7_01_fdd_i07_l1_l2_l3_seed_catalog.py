"""s7_01_fdd_i07_l1_l2_l3_seed_catalog

Adds L1/L2/L3 global seed catalog tables and extends L4 with parent_l3_id,
is_customer_facing, and typical_fit_decision columns.

Tables created conditionally (IF NOT EXISTS semantics) to support idempotent
execution against databases that already received these tables via db.create_all()
in a development environment.

Revision ID: a57ae6490f32
Revises: s6_01_fdd_i04_lessons_learned
Create Date: 2026-02-22 23:47:04.192482
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision = 'a57ae6490f32'
down_revision = 's6_01_fdd_i04_lessons_learned'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing = set(inspector.get_table_names())

    # ── L1 Seed Catalog ──────────────────────────────────────────────
    if 'l1_seed_catalog' not in existing:
        op.create_table(
            'l1_seed_catalog',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=10), nullable=False,
                      comment='Unique L1 code: L1-FI, L1-MM, L1-SD'),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('sap_module_group', sa.String(length=50), nullable=False,
                      comment='FI_CO | MM_WM | SD_CS | HR | BASIS'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code', name='uq_l1cat_code'),
        )

    # ── L2 Seed Catalog ──────────────────────────────────────────────
    if 'l2_seed_catalog' not in existing:
        op.create_table(
            'l2_seed_catalog',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('parent_l1_id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=15), nullable=False,
                      comment='Unique L2 code: L2-FI-AP, L2-MM-PUR'),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('sap_module', sa.String(length=10), nullable=False,
                      comment='Standard SAP module code: FI, MM, SD, CO…'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_s4_mandatory', sa.Boolean(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['parent_l1_id'], ['l1_seed_catalog.id'],
                                    ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code', name='uq_l2cat_code'),
        )

    # ── L3 Seed Catalog ──────────────────────────────────────────────
    if 'l3_seed_catalog' not in existing:
        op.create_table(
            'l3_seed_catalog',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('parent_l2_id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=20), nullable=False,
                      comment='Unique L3 code: L3-FI-AP-01'),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('sap_scope_item_id', sa.String(length=20), nullable=True,
                      comment='SAP scope item reference, e.g. J58, BD9'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('typical_complexity', sa.String(length=10), nullable=False,
                      server_default='medium',
                      comment='low | medium | high'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['parent_l2_id'], ['l2_seed_catalog.id'],
                                    ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code', name='uq_l3cat_code'),
        )

    # ── L4 Seed Catalog — extend with hierarchy link columns ─────────
    # Check which columns already exist to avoid duplicate-column errors.
    l4_cols = {c['name'] for c in inspector.get_columns('l4_seed_catalog')} if 'l4_seed_catalog' in existing else set()

    with op.batch_alter_table('l4_seed_catalog', schema=None) as batch_op:
        if 'parent_l3_id' not in l4_cols:
            batch_op.add_column(sa.Column(
                'parent_l3_id', sa.Integer(), nullable=True,
                comment='FK to L3SeedCatalog. nullable: existing records without hierarchy still valid.',
            ))
        if 'is_customer_facing' not in l4_cols:
            batch_op.add_column(sa.Column(
                'is_customer_facing', sa.Boolean(), nullable=False,
                comment='True = end-user facing L4 step (relevant for UAT scope).',
                server_default='0',
            ))
        if 'typical_fit_decision' not in l4_cols:
            batch_op.add_column(sa.Column(
                'typical_fit_decision', sa.String(length=20), nullable=True,
                comment='fit | partial_fit | gap — SAP best practice baseline estimate.',
            ))

    # Index + FK on l4 (skip if already present)
    l4_indexes = {i['name'] for i in inspector.get_indexes('l4_seed_catalog')} if 'l4_seed_catalog' in existing else set()
    if 'ix_l4_seed_catalog_parent_l3_id' not in l4_indexes:
        with op.batch_alter_table('l4_seed_catalog', schema=None) as batch_op:
            batch_op.create_index(
                batch_op.f('ix_l4_seed_catalog_parent_l3_id'),
                ['parent_l3_id'],
                unique=False,
            )


def downgrade():
    with op.batch_alter_table('l4_seed_catalog', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_l4_seed_catalog_parent_l3_id'))
        batch_op.drop_column('typical_fit_decision')
        batch_op.drop_column('is_customer_facing')
        batch_op.drop_column('parent_l3_id')

    op.drop_table('l3_seed_catalog')
    op.drop_table('l2_seed_catalog')
    op.drop_table('l1_seed_catalog')
