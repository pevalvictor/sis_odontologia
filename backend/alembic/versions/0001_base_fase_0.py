"""base fase 0 en español"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0001_base_fase_0"
down_revision=None
branch_labels=None
depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())

