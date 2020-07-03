import click
from click.types import DateTime
from datetime import datetime
import json
from os.path import abspath, join, dirname

from backends.jira import (
    ALL_ISSUES_FILENAME, DUMPFORMAT,
    fetch_all_issues)


here = abspath(dirname(__file__))
data_dir = join(here, 'datasets')


@click.group()
def cli():
    pass


@cli.command()
def extract():
    data = fetch_all_issues()
    print(here, data_dir)
    with open(join(data_dir, ALL_ISSUES_FILENAME), 'w') as f:
        json.dump([d.to_json() for d in data], f, indent=2)


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