from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, MetaData, Numeric, String, Table, Text, create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings


def build_database_url() -> str:
    user = settings.postgres_user
    password = settings.postgres_password
    host = settings.postgres_host
    port = settings.postgres_port
    db = settings.postgres_db

    if password:
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql+psycopg://{user}@{host}:{port}/{db}"


engine: Engine = create_engine(build_database_url(), pool_pre_ping=True, future=True)
metadata = MetaData()

competitors = Table(
    "competitors",
    metadata,
    Column("competitor_id", BigInteger, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("short_name", String(100), nullable=False),
    Column("brand_type", String(100), nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

service_plans = Table(
    "service_plans",
    metadata,
    Column("plan_id", BigInteger, primary_key=True),
    Column("competitor_id", BigInteger, nullable=False),
    Column("plan_name", String(255), nullable=False),
    Column("plan_category", String(100), nullable=False),
    Column("plan_type", String(100), nullable=False),
    Column("description", Text),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

plan_price_history = Table(
    "plan_price_history",
    metadata,
    Column("plan_price_history_id", BigInteger, primary_key=True),
    Column("plan_id", BigInteger, nullable=False),
    Column("effective_date", Date),
    Column("price_usd", Numeric(10, 2), nullable=False),
    Column("promotional_price_usd", Numeric(10, 2)),
    Column("promo_terms", Text),
    Column("features_snapshot", Text),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("source_snapshot_date", Date, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

devices = Table(
    "devices",
    metadata,
    Column("device_id", BigInteger, primary_key=True),
    Column("competitor_id", BigInteger, nullable=False),
    Column("manufacturer", String(150), nullable=False),
    Column("model_name", String(255), nullable=False),
    Column("device_type", String(100), nullable=False),
    Column("storage_variant", String(100)),
    Column("color", String(100)),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

device_price_history = Table(
    "device_price_history",
    metadata,
    Column("device_price_history_id", BigInteger, primary_key=True),
    Column("device_id", BigInteger, nullable=False),
    Column("effective_date", Date),
    Column("retail_price_usd", Numeric(10, 2), nullable=False),
    Column("promo_price_usd", Numeric(10, 2)),
    Column("promotion_terms", Text),
    Column("financing_terms", Text),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("source_snapshot_date", Date, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

promotions = Table(
    "promotions",
    metadata,
    Column("promotion_id", BigInteger, primary_key=True),
    Column("competitor_id", BigInteger, nullable=False),
    Column("promotion_title", String(255), nullable=False),
    Column("promotion_type", String(100), nullable=False),
    Column("description", Text, nullable=False),
    Column("target_type", String(50), nullable=False),
    Column("target_plan_id", BigInteger),
    Column("target_device_id", BigInteger),
    Column("start_date", Date),
    Column("end_date", Date),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

competitor_changes = Table(
    "competitor_changes",
    metadata,
    Column("change_id", BigInteger, primary_key=True),
    Column("competitor_id", BigInteger, nullable=False),
    Column("change_type", String(100), nullable=False),
    Column("entity_type", String(50), nullable=False),
    Column("entity_id", BigInteger, nullable=False),
    Column("previous_value", Text),
    Column("new_value", Text),
    Column("previous_snapshot_captured_at", DateTime(timezone=True)),
    Column("new_snapshot_captured_at", DateTime(timezone=True)),
    Column("change_detected_at", DateTime(timezone=True), nullable=False),
    Column("effective_date", Date),
    Column("severity", String(50), nullable=False),
    Column("summary_text", Text, nullable=False),
    Column("source_snapshot_from", Date),
    Column("source_snapshot_to", Date),
    Column("record_origin", String(30), nullable=False, server_default=text("'synthetic_seeded'")),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
