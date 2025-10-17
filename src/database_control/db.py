from src.config import CONFIG
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.logger import logger

engine = create_engine(CONFIG.POSTGRESQL_DSN)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    logger.info("get_db called - creating database session")
    db = SessionLocal()
    try:
        logger.info("Database session created successfully")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        logger.info("Closing database session")
        db.close()