from os.path import join

TRADING_BOARD = 140
TRADING_SPRINT_FOLDER = join('datasets', 'sprints', 'trading')
CX_BOARD = 130
CX_SPRINT_FOLDER = join('datasets', 'sprints', 'cx')
BILLING_BOARD = 145
BILLING_SPRINT_FOLDER = join('datasets', 'sprints', 'datarecs')

JIRA_SPRINTS_SOURCE_SINK = [
    (TRADING_BOARD, TRADING_SPRINT_FOLDER),
    (CX_BOARD, CX_SPRINT_FOLDER),
    (BILLING_BOARD, BILLING_SPRINT_FOLDER)
]
