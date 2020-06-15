from requests import get
from requests.auth import HTTPBasicAuth


MY_TOKEN = 'eVDgTL8kVgdXFaiJtbCF4001'
JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140

ISSUE_TYPES_NAME_ID = {
    'Story': 10315,
    'Subtask': 10354
}

STATUS_TYPES_NAME_ID = {
    'ToDO': 11490,
    'InProgress': 11491,
    'Done': 11492,
    'CodeReview': 11493,
}

trading_issues = get(
    JIRA_BASEURL + f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog',
    auth=HTTPBasicAuth(
        "grahame.gardiner@limejump.com",
        MY_TOKEN)).json()


print(
    trading_issues.keys(),
    trading_issues['total'],
    trading_issues['startAt'],
    trading_issues['maxResults'])

data = []
for issue in trading_issues['issues']:
    if (
            issue['fields']['status']['id'] == STATUS_TYPES_NAME_ID['Done'] and
            issue['fields']['issuetype']['id'] in (
                ISSUE_TYPES_NAME_ID.values())
       ):
        if not issue['fields']['subtasks']:
            histories = issue['changelog']['histories']
            status_changes = []
            for h in histories:
                s = {'timestamp': h['created']}
                for i in h['items']:
                    if i['fieldId'] == 'status':
                        s['from'] = i['from']
                        s['to'] = i['to']
                status_changes.append(s)
            data[issue['id']] = status_changes

issue_id = j['issues'][0]['id']
an_issue = get(
    f'https://limejump.atlassian.net/rest/api/2/issue/{issue_id}/transitions?expand=transitions',
    auth=HTTPBasicAuth(
        "grahame.gardiner@limejump.com",
        MY_TOKEN)).json()
print(an_issue)

print(an_issue)
issue_types = get(
    JIRA_BASEURL + "/2/issue"
)
