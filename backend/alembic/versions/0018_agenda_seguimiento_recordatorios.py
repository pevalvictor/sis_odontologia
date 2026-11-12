"""seguimiento y recordatorios de agenda"""
from alembic import op
import sqlalchemy as sa
revision="0018_agenda_fase5";down_revision="0017_citas_sesiones";branch_labels=None;depends_on=None
def upgrade():
    op.create_table("plantillas_recordatorio",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("clinica_id",sa.Integer(),sa.ForeignKey("clinicas.id",ondelete="CASCADE"),nullable=False),
        sa.Column("nombre",sa.String(120),nullable=False),
        sa.Column("canal",sa.String(20),nullable=False,server_default="interno"),
        sa.Column("asunto",sa.String(180),nullable=True),
        sa.Column("contenido",sa.Text(),nullable=False),
        sa.Column("variables",sa.Text(),nullable=True),
        sa.Column("activo",sa.Boolean(),nullable=False,server_default=sa.text("true")),
        sa.Column("fecha_creacion",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("fecha_actualizacion",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.UniqueConstraint("clinica_id","nombre",name="uq_plantillas_recordatorio_clinica_nombre"))
    op.create_index("ix_plantillas_recordatorio_clinica_id","plantillas_recordatorio",["clinica_id"])
    op.create_table("recordatorios_cita",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("clinica_id",sa.Integer(),sa.ForeignKey("clinicas.id",ondelete="CASCADE"),nullable=False),
        sa.Column("cita_id",sa.Integer(),sa.ForeignKey("citas.id",ondelete="CASCADE"),nullable=False),
        sa.Column("paciente_id",sa.Integer(),sa.ForeignKey("pacientes.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("plantilla_id",sa.Integer(),sa.ForeignKey("plantillas_recordatorio.id",ondelete="SET NULL"),nullable=True),
        sa.Column("canal",sa.String(20),nullable=False,server_default="interno"),
        sa.Column("destinatario",sa.String(180),nullable=True),
        sa.Column("mensaje",sa.Text(),nullable=False),
        sa.Column("estado",sa.String(20),nullable=False,server_default="pendiente"),
        sa.Column("fecha_programada",sa.DateTime(timezone=True),nullable=True),
        sa.Column("fecha_envio",sa.DateTime(timezone=True),nullable=True),
        sa.Column("usuario_envio_id",sa.Integer(),sa.ForeignKey("usuarios.id",ondelete="SET NULL"),nullable=True),
        sa.Column("observaciones",sa.Text(),nullable=True),
        sa.Column("fecha_creacion",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("fecha_actualizacion",sa.DateTime(timezone=True),server_default=sa.func.now()))
    op.create_index("ix_recordatorios_cita_clinica_id","recordatorios_cita",["clinica_id"])
    op.create_index("ix_recordatorios_cita_cita_id","recordatorios_cita",["cita_id"])
    op.create_check_constraint("ck_plantillas_recordatorio_canal","plantillas_recordatorio","canal IN ('interno','whatsapp','sms','email')")
    op.create_check_constraint("ck_recordatorios_cita_canal","recordatorios_cita","canal IN ('interno','whatsapp','sms','email')")
    op.create_check_constraint("ck_recordatorios_cita_estado","recordatorios_cita","estado IN ('pendiente','enviado','fallido','cancelado')")
def downgrade():
    op.drop_constraint("ck_recordatorios_cita_estado","recordatorios_cita",type_="check");op.drop_constraint("ck_recordatorios_cita_canal","recordatorios_cita",type_="check");op.drop_constraint("ck_plantillas_recordatorio_canal","plantillas_recordatorio",type_="check")
    op.drop_index("ix_recordatorios_cita_cita_id",table_name="recordatorios_cita");op.drop_index("ix_recordatorios_cita_clinica_id",table_name="recordatorios_cita");op.drop_table("recordatorios_cita")
    op.drop_index("ix_plantillas_recordatorio_clinica_id",table_name="plantillas_recordatorio");op.drop_table("plantillas_recordatorio")
