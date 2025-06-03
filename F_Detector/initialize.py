from mysql_handler import *
from trace_cover import get_all_builds, builds_to_json
import click
import json
import time


def save_data(builds):
    t1 = time.time()
    print("\n")
    failed_builds = []
    passed_builds = []
    failed_tests = {}

    for id, build in builds.items():
        if build['state'] == 'failed':
            failed_builds.append(build)
            if build['failed_info']:
                failed_tests[id] = build['failed_info']
        else:
            passed_builds.append(build)

    print("\n")
    if passed_builds:
        save_passed_builds(passed_builds)
    print("\n")
    if failed_builds and failed_tests:
        save_failed_builds_and_tests(failed_builds, failed_tests)
    t2 = time.time()
    print("save data cost " + str(t2 - t1) + " seconds")


def initialize(p, o, n, l):
    t1 = time.time()
    create_tables()
    save_case_and_smells(p)
    builds = get_all_builds(o, n, l)
    save_data(builds)
    update_flaky_frequency()
    update_detection_result(p)
    t2 = time.time()
    print("Done! total cost: " + str(t2 - t1))


def load_json(json_file):
    try:
        with open(json_file, 'r') as f:
            trace_json = json.load(f)
            return trace_json

    except IOError:
        print('Can not open the json file!')


def initialize_json(p, json_file):
    t1 = time.time()
    create_tables()
    save_case_and_smells(p)
    print("loading json file...")
    builds = load_json(json_file)
    save_data(builds)
    update_flaky_frequency()
    update_detection_result(p)
    t2 = time.time()
    print("Done! total cost: " + str(t2 - t1))


@click.command()
@click.option('--i', type=click.Choice(['init', 'init_json', 'builds2json']),
              help='init:get data from Travis; init_json: get data from json file')
@click.option('--j', help='json file path/name')
@click.option('--p', help='project path')
@click.option('--o', help='project owner on github')
@click.option('--n', help='project name on github')
@click.option('--l', type=int, default=3600, help='get the build history within [l] days')
def main(i, p, o, n, l, j):
    if i == 'init':
        initialize(p, o, n, l)
    elif i == 'init_json':
        initialize_json(p, j)
    elif i == 'builds2json':
        builds_to_json(o, n, l)


if __name__ == '__main__':
    main()
