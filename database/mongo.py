from dataclasses import dataclass
from pymongo import MongoClient
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

    def add_sprint(self, team_name, data):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']

        if team_id is None:
            log.error(
                'Team %s does not exist, check the migrations files'
                % team_name)
            return

        data['team_id'] = team_id
        try:
            db.sprints.insert_one(data)
        except DuplicateKeyError as e:
            assert e.details['keyValue']['_id'] == data['_id']
            log.info('Sprint with id %s already extracted' % data['_id'])

    def get_latest_sprint(self, team_name):
        db = self.client.sprints
        team_id = db.teams.find_one({'name': team_name})['_id']
        return list(db.sprints.find(
            {'team_id': team_id}).sort([('start', -1)]).limit(1)).pop()
