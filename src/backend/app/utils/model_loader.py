"""
Model loader — pre-loads all AI models at backend startup
when LAZY_LOADING is disabled.
"""

from app.core.logging_config import setup_logging

logger = setup_logging()


def load_all_models():
    """Load all AI model services into memory eagerly."""
    logger.info("Pre-loading all AI models at startup...")

    from app.services.parser import Parser
    Parser.get_instance()
    logger.info("  Parser model loaded")

    from app.services.task_matcher import task_matcher
    _ = task_matcher.model
    logger.info("  Task matcher model loaded")

    from app.services.img_to_prompt import ImgToPrompt
    ImgToPrompt.get_instance()
    logger.info("  Image-to-prompt service loaded")

    logger.info("All AI models loaded successfully")
