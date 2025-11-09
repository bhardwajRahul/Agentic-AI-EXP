import logging


def setup_logger(name: str = __name__) -> logging.Logger:
    """Configure and return a logger instance"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


request_counter = {"count": 0}
