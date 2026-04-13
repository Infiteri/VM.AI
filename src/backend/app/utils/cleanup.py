import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.draft import TaskDraft
from app.core.logging_config import setup_logging

# Initialize the logger for this module
logger = setup_logging()


def sweep_drafts(db: Session):
    """
    Deletes all drafts older than 24 hours.
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=24)
        count = db.query(TaskDraft).filter(TaskDraft.created_at < cutoff_time).count()
        
        if count > 0:
            db.query(TaskDraft).filter(TaskDraft.created_at < cutoff_time).delete()
            db.commit()
            logger.info(f"Cleanup: Deleted {count} old drafts.")
        else:
            logger.debug("Cleanup: No old drafts found.")
            
    except Exception as e:
        logger.error(f"Cleanup sweep failed: {e}")
        db.rollback()


async def run_cleanup_loop():
    """
    Runs the cleanup job immediately on start, then every 24 hours.
    This is a background task that runs indefinitely.
    """
    logger.info("Background Cleanup Service Initialized.")
    
    while True:
        db = SessionLocal()
        try:
            sweep_drafts(db)
        except Exception as e:
            logger.error(f"Critical error in cleanup loop: {e}")
        finally:
            db.close()
            
        # Sleep for 24 hours (86400 seconds)
        logger.info("Cleanup sleeping for 24 hours...")
        await asyncio.sleep(86400)
