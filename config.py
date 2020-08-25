from os.path import join

TRADING_BOARD = 140
TRADING_SPRINT_FOLDER = join('datasets', 'sprints', 'trading')
TRADING_HISTORIC_FOLDER = join('datasets', 'forecasting', 'trading')
CX_BOARD = 130
CX_SPRINT_FOLDER = join('datasets', 'sprints', 'cx')
CX_HISTORIC_FOLDER = join('datasets', 'forecasting', 'cx')
BILLING_BOARD = 145
BILLING_SPRINT_FOLDER = join('datasets', 'sprints', 'datarecs')
BILLING_HISTORIC_FOLDER = join('datasets', 'forecasting', 'datarecs')

JIRA_SPRINTS_SOURCE_SINK = [
    (TRADING_BOARD, TRADING_SPRINT_FOLDER),
    (CX_BOARD, CX_SPRINT_FOLDER),
    (BILLING_BOARD, BILLING_SPRINT_FOLDER)
]

JIRA_HISTORIC_SOURCE_SINK = [
    (TRADING_BOARD, TRADING_HISTORIC_FOLDER),
    (CX_BOARD, CX_HISTORIC_FOLDER),
    (BILLING_BOARD, BILLING_HISTORIC_FOLDER)
]

FOLDERS = {
    'cx': {
        'sprint': CX_SPRINT_FOLDER,
        'historic': CX_HISTORIC_FOLDER
    },
    'billing': {
        'sprint': BILLING_SPRINT_FOLDER,
        'historic': BILLING_HISTORIC_FOLDER
    },
    'trading': {
        'sprint': TRADING_SPRINT_FOLDER,
        'historic': TRADING_HISTORIC_FOLDER
    },
}
