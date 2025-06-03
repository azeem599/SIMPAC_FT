import time
import requests


def listener(project_owner, project_name, frequency):
    build_id = 0
    while True:
        url = 'https://api.travis-ci.org/repo/' + project_owner + '%2F' + \
              project_name + '/builds'
        params = {'include': 'build.jobs,build.commit',  # 'build.previous_state': 'passed',
                  'limit': 1, 'build.event_type': 'push'}  # only get the previous passed and now passed builds
        try:
            r = requests.get(url, headers={'Travis-API-Version': '3'}, params=params)
            build = r.json()
            current_build_id = build['builds'][0]['id']
            print(current_build_id)
            if build == 0:
                build_id = current_build_id
            elif build_id == current_build_id:
                continue
            else:
                pass
            time.sleep(frequency)
            # return build
        except Exception as e:
            print(e)


if __name__ == '__main__':
    project_owner = "apache"
    project_name = "incubator-superset"
    frequency = 10
    listener(project_owner, project_name, frequency)
