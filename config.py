from dataclasses import dataclass
from os.path import join
from typing import List

# FIXME: A fair amount of duplication...
TRADING_BOARD = 140
TRADING_HISTORIC_FOLDER = join('datasets', 'forecasting', 'trading')
CX_BOARD = 130
CX_HISTORIC_FOLDER = join('datasets', 'forecasting', 'cx')
BILLING_BOARD = 145
BILLING_HISTORIC_FOLDER = join('datasets', 'forecasting', 'datarecs')

JIRA_HISTORIC_SOURCE_SINK = [
    (TRADING_BOARD, TRADING_HISTORIC_FOLDER),
    (CX_BOARD, CX_HISTORIC_FOLDER),
    (BILLING_BOARD, BILLING_HISTORIC_FOLDER)
]

FOLDERS = {
    'cx': {
        'historic': CX_HISTORIC_FOLDER
    },
    'billing': {
        'historic': BILLING_HISTORIC_FOLDER
    },
    'trading': {
        'historic': TRADING_HISTORIC_FOLDER
    },
}


class ConfigClass:
    def __init__(self, dataclass):
        self.config_class = dataclass
        self.config = None

    def set(self, *a, **kw):
        if self.config is not None:
            raise ValueError(
                f'config for {self.config_class.__name__} already set')
        self.config = self.config_class(*a, **kw)

    def get(self):
        if self.config is not None:
            return self.config
        else:
            raise ValueError(
                f'config for {self.config_class.__name__} not set')


def configclass(dataclass):
    return ConfigClass(dataclass)


class Config:
    def __init__(self):
        self.config_store = {}

    def register(self, name, configclass):
        self.config_store[name] = configclass

    def get(self, name):
        return self.config_store[name].get()

    def set(self, name, *a, **kw):
        self.config_store[name].set(*a, **kw)


# The motivation for these config helpers is to enable the definition
# of config to be done near the usage site, but allow the setting of
# the actual config values to be done higher up as command line options,
# environment variables, or config files.
# Near the usage site you define a dataclass which captures the relevant
# config. Then call config.register, passing in the dataclass, to add it
# to the global store.
config = Config()


@dataclass
class TeamInfo:
    name: str
    board_id: int


@configclass
@dataclass
class StaticConfig:
    teams: List[TeamInfo]


config.register('static', StaticConfig)
config.set(
    'static',
    [
        TeamInfo('cx', 130),
        TeamInfo('dar', 145),
        TeamInfo('voyager', 140)
    ])
