import logging

LOG_FORMAT = "%(asctime)s [%(levelname)8s] {%(name)s} %(message)s"


def config_logging():
    for h in logging.root.handlers:
        logging.root.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)
    logging.root.addHandler(stdout_handler)
    logging.root.setLevel(logging.DEBUG)
