"""
Database configuration and session management for Multi-Tenant PostgreSQL
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database configuration - PostgreSQL required for multi-tenant
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hubsec:hubsec@localhost/hubsec_multitenant"
)

# Validate PostgreSQL
if "postgresql" not in DATABASE_URL:
    raise ValueError(
        "Multi-tenant mode requires PostgreSQL! "
        f"Current DATABASE_URL: {DATABASE_URL}. "
        "The multi-tenant schema uses PostgreSQL-specific types (UUID, INET, JSONB, ARRAY). "
        "For SQLite testing, use the original models.py and database.py"
    )

# Create database engine with PostgreSQL optimizations
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query debugging
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Max connections beyond pool_size
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get database session
def get_db():
    """
    Dependency function to get database session
    Ensures session is properly closed after request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Enable UUID extension (if not already enabled)
def enable_uuid_extension():
    """Enable PostgreSQL UUID extension"""
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.commit()


# Test database connection
def test_connection():
    """Test database connection and print info"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ PostgreSQL connected: {version}")

            # Check UUID extension
            result = conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp');")
            )
            uuid_enabled = result.scalar()
            if uuid_enabled:
                print("✅ UUID extension enabled")
            else:
                print("⚠️  UUID extension not enabled - will attempt to enable")
                enable_uuid_extension()
                print("✅ UUID extension enabled")

        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test connection when run directly
    test_connection()
