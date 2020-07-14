from os.path import join

TRADING_BOARD = 140
TRADING_SPRINT_FOLDER = join('datasets', 'sprints', 'trading')
CX_BOARD = 130
CX_SPRINT_FOLDER = join('datasets', 'sprints', 'cx')

JIRA_SPRINTS_SOURCE_SINK = [
    (TRADING_BOARD, TRADING_SPRINT_FOLDER),
    (CX_BOARD, CX_SPRINT_FOLDER)
]