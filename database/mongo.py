from dataclasses import dataclass
from pymongo import MongoClient, ReplaceOne
from pymongo.errors import DuplicateKeyError
import logging

from config import config, configclass


log = logging.getLogger(__name__)
log.setLevel('INFO')


@configclass
@dataclass
class DBConfig:
    host: str
    port: int
    username: str
    password: str


config.register('db', DBConfig)


class Client:
    def __init__(self):
        conn_info = config.get('db')
        self.client = MongoClient(
            host=conn_info.host,
            port=conn_info.port,
            username=conn_info.username,
            password=conn_info.password)

    def add_historic_issues(self, team_name, issues):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']

        if team_id is None:
            log.error(
                'Team %s does not exist, check the migrations files'
                % team_name)
            return

        for issue in issues:
            issue['team_id'] = team_id

        # As time goes on issues move in to Done, thus becoming "historic"
        # We do a replace-upsert to both capture new historic issues and
        # update the old issues if any changes have been made.
        replacements = [
            ReplaceOne({"name": issue['name']}, issue, upsert=True)
            for issue in issues
        ]
        res = db.historic_issues.bulk_write(replacements)

        if res.bulk_api_result['writeErrors']:
            log.error(res.bulk_api_result['writeErrors'])

        log.info(
            'Replaced historic issues for %s' % team_name)

    def get_historic_issues(self, team_name):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']
        return list(db.historic_issues.find({"team_id": team_id}))

    def get_sprint(self, sprint_id):
        db = self.client.sprints
        return db.sprints.find_one({'_id': sprint_id})

    def add_sprint(self, team_name, data):
        db = self.client.sprints
        team = db.teams.find_one({'name': team_name})

        if team is None:
            team_id = self.add_team(team_name)
            log.info('Added new team %s' % team_name)
        else:
            team_id = team['_id']

        data['team_id'] = team_id
        try:
            db.sprints.insert_one(data)
        except DuplicateKeyError as e:
            assert e.details['keyValue']['_id'] == data['_id']
            log.info('Sprint with id %s already extracted' % data['_id'])

    def add_team(self, team_name):
        db = self.client.sprints
        res = db.teams.insert_one({'name': team_name})
        return res.inserted_id

    def get_sprint_auxillary_data(self, sprint_id):
        db = self.client.sprints
        return db.sprints_aux.find_one({'sprint_id': sprint_id}) or {}

    def update_sprint_auxillary_data(self, sprint_id, data):
        db = self.client.sprints
        data['sprint_id'] = sprint_id
        db.sprints_aux.replace_one(
            {'sprint_id': sprint_id},
            data,
            upsert=True)

    def get_latest_sprint(self, team_name):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']
        return list(db.sprints.find(
            {'team_id': team_id}).sort([('start', -1)]).limit(1)).pop()

    def get_sprints(self, team_name, ending_after):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']
        return list(db.sprints.find(
            {
                'team_id': team_id,
                'end': {
                    '$gte': ending_after}
            }).sort([('start', -1)]))

    def get_sprints_and_aux(self, team_name, ending_after):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']
        return list(db.sprints.aggregate([
            {
                "$match": {
                    "team_id": team_id,
                    "end": {"$gte": ending_after}
                }
            },
            {
                "$lookup": {
                    "from": "sprints_aux",
                    "localField": "_id",
                    "foreignField": "sprint_id",
                    "as": "auxillary_data"
                }
            },
            {
                "$sort": {"start": -1}
            }
        ]))

    def update_performance_report(self, sprint_id, data):
        db = self.client.sprints
        db.performance_reports.update_one(
            {'_id': sprint_id},
            {'$set': data})

    def update_performance_reports(self, sprint_reports):
        db = self.client.sprints

        # Generally we will just generate reports for the most recent
        # sprint. But if people are late updateing a manual input such
        # as goal completion, it is useful to be able to replace existing
        # reports.
        replacements = [
            ReplaceOne(
                {"_id": report['_id']}, report, upsert=True)
            for report in sprint_reports
        ]
        res = db.performance_reports.bulk_write(replacements)

        if res.bulk_api_result['writeErrors']:
            log.error(res.bulk_api_result['writeErrors'])

        log.debug('Updated recent sprint reports')

    def get_performance_reports(self, ending_after):
        db = self.client.sprints
        return list(db.performance_reports.find(
            {'end_date': {'$gte': ending_after}}
            ).sort([('start_date', -1)]))

    def update_bau_reports(self, bau_reports):
        db = self.client.sprints

        # FIXME: repetition with performance
        replacements = [
            ReplaceOne(
                {"_id": report['_id']}, report, upsert=True)
            for report in bau_reports
        ]
        res = db.bau_reports.bulk_write(replacements)

        if res.bulk_api_result['writeErrors']:
            log.error(res.bulk_api_result['writeErrors'])

        log.debug('Updated recent sprint reports')

    def get_bau_reports(self, ending_after):
        db = self.client.sprints
        return list(db.bau_reports.find(
            {'end_date': {'$gte': ending_after}}
            ).sort([('start_date', -1)]))


_client = None


def get_client():
    global _client
    if not _client:
        _client = Client()
    return _client
