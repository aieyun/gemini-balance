from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('status', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('failure_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), 
                 server_default=sa.func.now(), 
                 onupdate=sa.func.now(),
                 nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_key', 'api_keys', ['key'], unique=True)

def downgrade():
    op.drop_index('ix_api_keys_key', 'api_keys')
    op.drop_table('api_keys') 