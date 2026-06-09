import os
import loguru
import sys

current_path=os.path.abspath(__file__)
log_path=os.path.join(os.path.dirname(current_path),'logs')

def get_logger():
    logger=loguru.logger
    logger.remove()

    os.makedirs(log_path,exist_ok=True)

    format_id=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}></cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level='DEBUG',
        format=format_id
    )

    logger.add(
        os.path.join(log_path,'info.log'),
        retention='30 days',
        rotation='9 MB',
        level='INFO',
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    )

    logger.add(
        os.path.join(log_path,'error.log'),
        retention='30 days',
        rotation='9 MB',
        level='ERROR',
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    )

    return logger

logger=get_logger()


    