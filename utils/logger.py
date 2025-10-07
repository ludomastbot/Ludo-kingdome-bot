import logging
import sys
from config import config

def setup_logger():
    logger = logging.getLogger('ludo_bot')
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
