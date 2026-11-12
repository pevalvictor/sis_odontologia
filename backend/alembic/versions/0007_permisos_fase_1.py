"""permisos y datos base fase 1"""
from alembic import op
from sqlalchemy.orm import Session
from app.db.semillas import sembrar_fase1
revision="0007_permisos_fase_1";down_revision="0006_cotizaciones_planes";branch_labels=None;depends_on=None
def upgrade():
    with Session(bind=op.get_bind()) as s:sembrar_fase1(s);s.commit()
def downgrade():pass
