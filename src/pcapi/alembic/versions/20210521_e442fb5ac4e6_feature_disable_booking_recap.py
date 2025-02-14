"""feature_disable_booking_recap

Revision ID: e442fb5ac4e6
Revises: 8824ce692699
Create Date: 2021-05-21 09:33:28.418695

"""
from pcapi.models import feature


# revision identifiers, used by Alembic.
revision = "e442fb5ac4e6"
down_revision = "8824ce692699"
branch_labels = None
depends_on = None

FLAG = feature.FeatureToggle.DISABLE_BOOKINGS_RECAP_FOR_SOME_PROS


def upgrade() -> None:
    feature.add_feature_to_database(FLAG)


def downgrade() -> None:
    feature.remove_feature_from_database(FLAG)
