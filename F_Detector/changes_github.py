import re
import os
import subprocess
from functools import wraps
import requests
import time

token = 'eae3919c1edac42652da2016842621ba895ef5e1'


def get_diff(commit_sha, project_path):
    os.chdir(project_path)
    diff_command = 'git diff ' + commit_sha + "^^!"  # why it works with ^^, not ^ ???

    result = subprocess.Popen(diff_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.readlines()
    m = 0
    change_dic = {}
    temp_file = ''
    py_file_number = 0
    other_file_number = 0
    py_found = True
    change_dic['diff'] = 'Y'
    if not output:
        change_dic['diff'] = 'N'

    for line in output:
        line = str(line, encoding="utf-8")
        print(line)
        line.strip()
        # line.replace('\n', '')
        # print(line)
        m += 1

        if line.startswith('+++ b') and (line.endswith('.py\n') or line.endswith('.pyx\n')):
            # print(line)
            py_file_number += 1
            temp_file = re.findall(r'[/](.+?[.]py.*)', line)[0]
            change_dic[temp_file] = []
            py_found = True

        elif line.startswith('@@') and py_found:
            change_list = []
            num = re.findall(r'[+](.+?[ ])', line)[0]
            num_list = re.split(r'[,]', num)
            start = int(num_list[0])
            end = int(num_list[0]) + int(num_list[1]) - 1
            change_list.append(start)
            change_list.append(end)
            change_dic[temp_file].append(change_list)

        elif line.startswith('+++ b') and not (line.endswith('.py\n') or line.endswith('.pyx\n')):
            other_file_number += 1
            py_found = False

    return change_dic, py_file_number, other_file_number


def func_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        print('[Function: {name} start...]'.format(name=function.__name__))
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print('[Function: {name} finished, spent time: {time:.2f}s]'.format(name=function.__name__, time=t1 - t0))
        return result

    return function_timer


def connect_url(url):
    headers = {
        'Accept': "application/vnd.github.v3+json", 'Authorization': 'token ' + token}
    s = requests.Session()
    request = s.get(url, headers=headers, stream=True)
    r = request.json()
    return r


def git_compare(commit, slug):
    compare_url = 'https://api.github.com/repos/' + slug + '/compare/' + commit
    res = connect_url(compare_url)
    # print(res)
    return res


def git_pull(pull_number, slug):
    compare_url = 'https://api.github.com/repos/' + slug + '/pulls/' + pull_number + '/files' + '?per_page=100'
    res = connect_url(compare_url)
    return res


def git_commit(commit_sha, slug):
    compare_url = 'https://api.github.com/repos/' + slug + '/commits/' + commit_sha
    res = connect_url(compare_url)
    return res


@func_timer
def get_changed_files(commit, slug):
    if len(commit) < 7:
        return git_pull(commit, slug)
    elif '...' not in commit:
        return git_commit(commit, slug)
    else:
        return git_compare(commit, slug)


# @func_timer
def get_changes(commit, slug):
    res = get_changed_files(commit, slug)
    change_dic = {'diff': 'Y'}
    if isinstance(res, list) or 'documentation_url' not in res.keys():
        if len(commit) < 7:
            files = res
        else:
            files = res['files']
        for file in files:
            if 'patch' in file.keys() and (file['filename'].endswith('.py') or file['filename'].endswith('.pyx')):
                filename = file['filename']
                change_dic[filename] = []
                num = re.findall(r'[+]([0-9]+[,][0-9]+) @', file['patch'])
                for n in num:
                    num_list = re.split(r'[,]', n)
                    start = int(num_list[0])
                    end = int(num_list[0]) + int(num_list[1]) - 1
                    change_list = [start, end]
                    change_dic[filename].append(change_list)
    else:
        change_dic['diff'] = 'N'
    return change_dic


if __name__ == '__main__':
    sha = '8f6555df4e1596070d758a395dec2ef2dbd7b373'
    path = r'D:\CoursesResources\MasterThesis\Python_projects\spaCy'
    slug = 'explosion/spaCy'
    compare = '4612'
    # print(get_diff(sha, path))
    # get_parent(sha, slug)
    get_changes(compare, slug)
