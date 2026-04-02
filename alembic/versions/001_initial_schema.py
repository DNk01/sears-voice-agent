"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "technicians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_technicians_id", "id"),
    )

    op.create_table(
        "service_areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "specialties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("appliance_type", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "availability_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("is_booked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(), nullable=False),
        sa.Column("customer_phone", sa.String(), nullable=False),
        sa.Column("customer_email", sa.String()),
        sa.Column("appliance_type", sa.String(50), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.ForeignKeyConstraint(["slot_id"], ["availability_slots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "image_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime()),
        sa.Column("image_path", sa.String()),
        sa.Column("analysis_result", sa.Text()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_image_requests_session_id", "image_requests", ["session_id"])
    op.create_index("ix_image_requests_token", "image_requests", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_image_requests_token", table_name="image_requests")
    op.drop_index("ix_image_requests_session_id", table_name="image_requests")
    op.drop_table("image_requests")
    op.drop_table("appointments")
    op.drop_table("availability_slots")
    op.drop_table("specialties")
    op.drop_table("service_areas")
    op.drop_table("technicians")
