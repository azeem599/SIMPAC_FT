import csv
import click
from initialize import save_data, load_json
from trace_cover import *
import mysql_handler as mh
from datetime import datetime
from changes_github import func_timer


@func_timer
def update_from_Travis(project_path, project_owner, project_name):
    latest_build_created_time = mh.search_latest_build_created_time()
    if len(latest_build_created_time) > 0:
        start_time = latest_build_created_time[0][0]
        now = datetime.now()
        timeDiff = now - start_time
        days = timeDiff.days + 1
        builds = get_all_builds(project_owner, project_name, days)
        save_data(builds)
        mh.update_flaky_frequency(start_time)
        mh.update_detection_result(project_path, start_time)
    else:
        print('Already up to date')


@func_timer
def update_from_json(project_path, json_file):
    builds = load_json(json_file)
    save_data(builds)
    mh.update_flaky_frequency()
    mh.update_detection_result(project_path)


@func_timer
def update_training_data(build_id, test_method, label):
    res = mh.search_factors(str(build_id), test_method)
    if len(res) > 0 and label in [0, 1]:
        with open('dataset.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            factors = [test_method, str(build_id)]
            for r in res[0]:
                if r == 'F':
                    r = 0
                elif r == 'T':
                    r = 1
                factors.append(r)
            factors.append(label)
            writer.writerow(factors)
            print('update training data done!')
    elif len(res) == 0:
        print('No such build_id and test_method in DB!')
    else:
        print('Wrong label! label can only be 0 or 1')


@func_timer
def update_multi_factor_results():
    mh.update_multi_results()


@click.command()
@click.option('--update', type=click.Choice(['travis', 'json', 'data', 'results']),
              help='travis:update build history from Travis; json: update build history from json file;'
                   'data: update training data; smells: update smells to a certain commit')
@click.option('--j', help='json file path/name')
@click.option('--p', help='project path')
@click.option('--o', help='project owner on github')
@click.option('--n', help='project name on github')
@click.option('--id', type=int, help='build id')
@click.option('--test', help='test method name')
@click.option('--label', type=int, help='test method name')
def main(update, j, p, o, n, id, test, label):
    if update == 'travis':
        update_from_Travis(p, o, n)
    elif update == 'json':
        update_from_json(p, j)
    elif update == 'data':
        update_training_data(id, test, label)
    elif update == 'results':
        update_multi_factor_results()


if __name__ == '__main__':
    main()
