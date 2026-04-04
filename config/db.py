from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from os import environ
from dotenv import load_dotenv

load_dotenv()

# Use DATABASE_URL if provided (for Flower and other services that don't need individual vars)
# Otherwise, build it from individual environment variables
DATABASE_URL = environ.get("DATABASE_URL")

if not DATABASE_URL:
    mysql_host = environ.get("MYSQL_HOST")
    mysql_port = environ.get("MYSQL_PORT")
    mysql_username = environ.get("MYSQL_USERNAME")
    mysql_password = environ.get("MYSQL_ROOT_PASSWORD")
    mysql_database = environ.get("MYSQL_DATABASE")
    
    # Create the database URL
    DATABASE_URL = f"mysql+mysqlconnector://{mysql_username}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"

# Create engine with connection pooling for production
db_engine = create_engine(
    DATABASE_URL,
    pool_size=15,              # Max connections to keep open (optimized for 8-core 16GB server)
    max_overflow=10,           # Additional connections when pool is full
    pool_timeout=30,           # Timeout waiting for connection (seconds)
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Test connections before use
    echo=False,                # Disable SQL logging in production
    echo_pool=False            # Disable pool logging
)
metadata = MetaData()
con = db_engine.connect()

# Create SessionLocal once (reused by all requests)
SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
Base = declarative_base()
Base = declarative_base()

# Note: Avoid importing model modules here to prevent circular imports.
# Models should import Base from this module. The application or Alembic
# can import model modules as needed during initialization/migrations.