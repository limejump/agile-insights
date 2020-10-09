import click
from itertools import chain
import logging
import sys

from backends.jira import fetch_all_completed_issues, fetch_sprints

from config import config
from database.mongo import Client


logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ])


@click.group()
def cli():
    pass


@cli.group()
def extract():
    pass


@extract.command()
@click.argument('access-token', envvar='TOKEN')
@click.argument('db-host', envvar='DB_HOST', default='localhost')
@click.argument('db-port', envvar='DB_PORT', type=int, default=27017)
@click.argument('db-username', envvar='DB_USERNAME', default='root')
@click.argument('db-password', envvar='DB_PASSWORD', default='rootpassword')
def issues(access_token, db_host, db_port, db_username, db_password):
    config.set('jira', access_token)
    config.set('db', db_host, db_port, db_username, db_password)
    db_client = Client()

    for team in config.get('static').teams:
        data = fetch_all_completed_issues(team.board_id)
        db_client.add_historic_issues(
            team.name,
            list(chain(*[d.to_json() for d in data])))


@extract.group()
def sprints():
    pass


@sprints.command()
@click.argument('access-token', envvar='TOKEN')
@click.argument('db-host', envvar='DB_HOST', default='localhost')
@click.argument('db-port', envvar='DB_PORT', type=int, default=27017)
@click.argument('db-username', envvar='DB_USERNAME', default='root')
@click.argument('db-password', envvar='DB_PASSWORD', default='rootpassword')
def latest(access_token, db_host, db_port, db_username, db_password):
    config.set('jira', access_token)
    config.set('db', db_host, db_port, db_username, db_password)
    db_client = Client()

    for team in config.get('static').teams:
        data = fetch_sprints(team.board_id)
        for sprint_data in data:
            db_client.add_sprint(team.name, sprint_data)


if __name__ == '__main__':
    cli()
