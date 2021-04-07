import click
import click_config_file
from itertools import chain
import logging
import sys

from backends.jira import fetch_all_completed_issues, fetch_sprints

from config import config, json_provider, parse_teams_input
from database.mongo import get_client
from reports.sprint_performance import create_reports as create_performance_reports


logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ])

log = logging.getLogger(__name__)
log.setLevel('INFO')


@click.group()
def cli():
    pass


@cli.group()
def extract():
    pass


def check_jira_config(team, url, email):
    error_message = ''
    if not team:
        error_message += (
            "\n- No teams specified for data extraction, either:\n"
            "  * supply teams with --team <name board_id>..\n"
            "  * or supply a json config file with --config \n")
    if not url:
        error_message += (
            "\n- No jira url provided, specify using:\n"
            "  * JIRA_URL envvar, --jira-url, or --config  file\n"
        )
    if not email:
        error_message += (
            "\n- No jira user email provided, specify using:\n"
            "  * JIRA_EMAIL envvar, --jira-user-email, or --config  file\n"
        )
    if error_message:
        raise click.UsageError(error_message)


@extract.command()
@click.argument('access-token', envvar='JIRA_TOKEN')
@click.argument('db-host', envvar='DB_HOST', default='localhost')
@click.argument('db-port', envvar='DB_PORT', type=int, default=27017)
@click.argument('db-username', envvar='DB_USERNAME', default='root')
@click.argument('db-password', envvar='DB_PASSWORD', default='rootpassword')
@click.option(
    '--jira-url', envvar='JIRA_URL',
    help=('alternatively provide this in a --config file'))
@click.option(
    '--jira-user-email', envvar='JIRA_EMAIL',
    help=('alternatively provide this in a --config file'))
@click.option(
    '--team', type=(str, int),  multiple=True,
    help=(
        '(team name, board id), '
        'alternatively provide these in --config file'))
@click_config_file.configuration_option(
    provider=json_provider, implicit=False)
def issues(
        team,
        jira_url, jira_user_email, access_token,
        db_host, db_port, db_username, db_password):
    check_jira_config(team, jira_url, jira_user_email)
    config.set('jira', jira_url, jira_user_email, access_token)
    config.set('teams', parse_teams_input(team))
    config.set('db', db_host, db_port, db_username, db_password)
    db_client = get_client()
    for team in config.get('teams').teams:
        log.info(f'Extracting Issue history for {team}')
        data = fetch_all_completed_issues(team.board_id)
        db_client.add_historic_issues(
            team.name,
            list(chain(*[d.to_mongo() for d in data])))


@extract.group()
def sprints():
    pass


@sprints.command()
@click.argument('access-token', envvar='JIRA_TOKEN')
@click.argument('db-host', envvar='DB_HOST', default='localhost')
@click.argument('db-port', envvar='DB_PORT', type=int, default=27017)
@click.argument('db-username', envvar='DB_USERNAME', default='root')
@click.argument('db-password', envvar='DB_PASSWORD', default='rootpassword')
@click.option(
    '--jira-url', envvar='JIRA_URL',
    help=('alternatively provide this in a --config file'))
@click.option(
    '--jira-user-email', envvar='JIRA_EMAIL',
    help=('alternatively provide this in a --config file'))
@click.option(
    '--team', type=(str, int),  multiple=True,
    help=(
        '(team name, board id), '
        'alternatively provide these in --config file'))
@click_config_file.configuration_option(
    provider=json_provider, implicit=False)
def latest(
        team,
        jira_url, jira_user_email, access_token,
        db_host, db_port, db_username, db_password):
    check_jira_config(team, jira_url, jira_user_email)
    config.set('jira', jira_url, jira_user_email, access_token)
    config.set('teams', parse_teams_input(team))
    config.set('db', db_host, db_port, db_username, db_password)
    db_client = get_client()

    for team in config.get('teams').teams:
        log.info(f'Extracting sprint data for {team}')
        data = fetch_sprints(team.board_id)
        for sprint_data in data:
            db_client.add_sprint(team.name, sprint_data)

    log.info('Updating all sprint reports')
    reports = create_performance_reports(config.get('teams').teams)
    db_client.update_performance_reports(reports.to_dict(orient='records'))


@cli.group()
def generate():
    pass


@generate.command()
@click.argument('db-host', envvar='DB_HOST', default='localhost')
@click.argument('db-port', envvar='DB_PORT', type=int, default=27017)
@click.argument('db-username', envvar='DB_USERNAME', default='root')
@click.argument('db-password', envvar='DB_PASSWORD', default='rootpassword')
@click.option(
    '--team', type=(str, int),  multiple=True,
    help=(
        '(team name, board id), '
        'alternatively provide these in --config file'))
@click_config_file.configuration_option(
    provider=json_provider, implicit=False)
def sprint_reports(
        team,
        db_host, db_port, db_username, db_password):
    config.set('teams', parse_teams_input(team))
    config.set('db', db_host, db_port, db_username, db_password)
    db_client = get_client()

    log.info('Updating all sprint reports')
    reports = create_performance_reports(config.get('teams').teams)
    db_client.update_performance_reports(reports.to_dict(orient='records'))


if __name__ == '__main__':
    cli()
