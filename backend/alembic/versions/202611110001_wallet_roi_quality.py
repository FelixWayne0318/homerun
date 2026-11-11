"""Persist wallet ROI data-quality metadata.

``avg_roi`` can now be exact, estimated from upstream percentages, or
unknown when no usable cost basis exists. The two columns keep that state
visible to the API and UI instead of forcing callers to infer it from a
surprising percentage.

Nullable on purpose: legacy rows keep NULL until re-analysis.

Revision ID: 202611110001
Revises: 202608190001
Create Date: 2026-11-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from alembic_helpers import column_names, safe_add_column


revision = "202611110001"
down_revision = "202608190001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    safe_add_column("discovered_wallets", sa.Column("roi_quality", sa.String(), nullable=True))
    safe_add_column("discovered_wallets", sa.Column("cost_coverage", sa.Float(), nullable=True))


def downgrade() -> None:
    existing = column_names("discovered_wallets")
    if "cost_coverage" in existing:
        op.drop_column("discovered_wallets", "cost_coverage")
    if "roi_quality" in existing:
        op.drop_column("discovered_wallets", "roi_quality")
