# Agile Insights

The motivation for this project is to gain useful insights from tracked software development work in order to:
- provide data informed estimation to better communicate delivery timelines
- help target problem areas in codebases that need urgent attention

In many ways it's also a research project. I've always had the belief that it is impossible to accurately estimate a delivery timeline for software projects;
In this project I analyse real data from Jira to explore if my hypothesis is actually true.

## Architecture

The codebase is split into two main parts:
- Data extraction (currently only support for Jira)
- A `Dash`board to display and use the data

In a nutshell, the data extraction jobs are python ETL's that fetch and transform data form Jira, and load it into mongodb.
The dashboard displays the data stored in mongodb in a visual form.

There are three main parts of the dashboard:
- The sprints breakdown view, which displays delivery percentage, some notes, percentages of planned and unplanned work...
- A forecasting view, where you can provide time-window delivery estimates calculated using:
  - Accumulated velocity from the past 6 sprints
  - or Monte-Carlo simulations based on historic delivery of issues
- A Metrics view, which aggregates the past 6 sprints worth of data, displayed individually in the Sprints view.

In the Sprints view there is some data and from inputs that are rather specific to my current workplace.
In particular we capture the percentage of issues tagged as BAU (Business As Usual) which is a sort of developer distraction metric.
We also track sprint goal completion via a toggle that can be switched to represent Pass/Fail.

## Set up python environment

I typically set up a python virtual environment. There is extensive documentation on the web for this.

Install with test dependencies:

```
pip install -e .'[test]'
```

Install migrations

```
pip install -r database/migration-requirements.txt
```

## Run tests

```
pytest tests
```

## Local Development

I've provided lots of options, but I'll outline my preferred one here.


### Deploy a local mongodb docker container

You will need to modify the `mongodb.volumes` section to provide your own local data directory.

```
docker-compose up mongodb
```

port 27017 wil be exposed.

You can then run the migrations

```
export DB_PASSWORD=rootpassword
export DB_HOST=localhost
pymongo-migrate upgrade -u "mongodb://root:${DB_PASSWORD}@${DB_HOST}:27017/sprints?authSource=admin" -m migrations
```

### Create your config file

Make a new `config.json` file in the `config_files` directory following the format of the provided `config_files/example_config.json`.

### Run data collection scripts

```
python cli.py extract sprints latest <JIRA_ACCESS_TOKEN> --config=config_files/config.json
```

```
python cli.py extract issues <JIRA_ACCESS_TOKEN> --config=config_files/config.json
```

You can alternatively opt out of using a config file, but you will need to provide all the details via command line parameters, for example:

```
python cli.py extract issues <JIRA_ACCESS_TOKEN> --jira-url=<jira-url> --jira-user-email=<email> --team <team_name> <board_id> --team <team_name> <board_id> ...
```

### Run the dashboard

The app currently requires a `./config_files/config.json` file to read the teams from.

```
python app.py
```

This spins up the `Dash` development server, connected to mongodb.

## Pre-Production deployment

In the `k8s` folder all of the required resources are provided to deploy the system as a whole to a local kubernetes cluster. My preference is [microk8s](https://microk8s.io/).

You will need to deploy both secrets first:
```
kubectl apply -f k8s/<secret-file>
```
Followed by the helm chart. It's easiest to first clone the [helm chart](https://github.com/limejump/agile-insights-chart) locally.
```
helm3 install agile-insights --values k8s/agile-insights-values.yaml <local-path-to-helm-chart>
```
