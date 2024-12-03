import logging
import os
from datetime import datetime
import re

class NoColorFormatter(logging.Formatter):
    """
    A logging formatter that removes ANSI escape codes from log messages.
    """
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

    def format(self, record):
        original_msg = super().format(record)
        clean_msg = self.ansi_escape.sub('', original_msg)
        return clean_msg


def init_logging(name='gamelog'):
    logdir = "risk/logs"

    if not os.path.exists(logdir):
        os.makedirs(logdir)

    timestamp = datetime.now().strftime("%Y_%d_%m_%H_%M_%S")
    log_filename = f"{name}_{timestamp}.log"
    log_filepath = os.path.join(logdir, log_filename)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    color_formatter = logging.Formatter('%(message)s')  # Keeps ANSI codes
    no_color_formatter = NoColorFormatter('%(message)s')  
    
    # File handler - logs to file without color codes
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setFormatter(no_color_formatter)
    logger.addHandler(file_handler)
    
    # Stream handler - logs to console with color codes
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(color_formatter)
    logger.addHandler(stream_handler)
