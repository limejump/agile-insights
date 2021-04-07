from os import environ
from config import config

from .forecast import Forecast
from .sprint import SprintReadWrite, Sprints, Metrics

config.set(
    'db',
    environ.get('DB_HOST', 'localhost'),
    int(environ.get('DB_PORT', 27017)),
    environ.get('DB_USERNAME', 'root'),
    environ.get('DB_PASSWORD', 'rootpassword'),
    )
