import logging
import os
from logging.handlers import RotatingFileHandler

LOGS_PATH = os.path.join("out", "logs")
VERIFIER_RESOURCES_PATH = os.path.join("res", "verifier")
LOOKUP_RESOURCES_PATH = os.path.join("res", "lookup")

os.makedirs(LOGS_PATH, exist_ok=True)
os.makedirs(VERIFIER_RESOURCES_PATH, exist_ok=True)
os.makedirs(LOOKUP_RESOURCES_PATH, exist_ok=True)

LOOKUP_LOG_FILE = os.path.join(LOGS_PATH, "lookup.log")
LOOKUP_CONFIG_FILE = os.path.join(LOOKUP_RESOURCES_PATH, "config.json")

VERIFIER_LOG_FILE = os.path.join(LOGS_PATH, "verifier.log")
VERIFIER_KEY_FILE = os.path.join(VERIFIER_RESOURCES_PATH, "key")
VERIFIER_CONFIG_FILE = os.path.join(VERIFIER_RESOURCES_PATH, "config.json")


def prepare_start(config_file, log_file, config, logger):
    if os.path.isfile(config_file):
        config.load(config_file)
    else:
        logger.warning(f"Config file '{config_file}' not found!")

    handler = RotatingFileHandler(log_file, maxBytes=10000, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s\n%(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
