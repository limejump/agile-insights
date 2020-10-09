import click
from click.types import DateTime
from datetime import datetime
from itertools import chain
import json
import logging
from os.path import abspath, join, dirname
import sys

from backends.jira import (
    ALL_ISSUES_FILENAME, DUMPFORMAT,
    fetch_all_completed_issues, fetch_sprints)

from config import (
    JIRA_HISTORIC_SOURCE_SINK,
    config)

from database.mongo import Client

here = abspath(dirname(__file__))
data_dir = join(here, 'datasets')


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


@cli.group()
def dump():
    pass


@dump.command(help="If neither --start or --end is specified return all")
@click.option('--start', type=DateTime())
@click.option('--end', type=DateTime())
def range(start, end):
    # FIXME: Repitition
    try:
        with open(join(data_dir, ALL_ISSUES_FILENAME), 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise click.ClickException("please run `extract`")

    if start is end is None:
        click.echo(
            f'file dumped at: {join(data_dir, ALL_ISSUES_FILENAME)}')
        return

    filename = 'jira-dataset'
    datetime_predicates = []
    if start:
        filename += f'-from-{datetime.strftime(start, DUMPFORMAT)}'
        datetime_predicates.append(
            lambda i: start <= datetime.strptime(
                i['metrics']['resolution_date'], DUMPFORMAT))
    if end:
        filename += f'-to-{datetime.strftime(end, DUMPFORMAT)}'
        datetime_predicates.append(
            lambda i: datetime.strptime(
                i['metrics']['resolution_date'], DUMPFORMAT) <= end)
    filename += '.json'
    filepath = join(data_dir, filename)
    with open(filepath, 'w') as f:
        json.dump(
            [d for d in data if all((p(d) for p in datetime_predicates))],
            f, indent=2)

    click.echo(f'file dumped at: {join(data_dir, filepath)}')


if __name__ == '__main__':
    cli()
