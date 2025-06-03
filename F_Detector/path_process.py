import os
import re
import platform


def get_abspath(project_path, relative_path, file):

    system = platform.system()
    if system == 'Windows':
        system_path = '\\'
        if relative_path.endswith('/'):
            relative_path = re.findall('(.+?)[/]$', relative_path)[0].replace('/', '\\')
        else:
            relative_path = relative_path.replace('/', '\\')
    else:
        system_path = '/'
    path = relative_path + system_path + file
    for relpath, dirs, files in os.walk(project_path):
        if file in files:
            full_path = os.path.join(relpath, file)
            if full_path.endswith(path):
                # print(full_path)
                return full_path


def get_test_files(project_path):

    test_files_list = list()
    for relpath, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                if file.startswith('test_') or file.endswith('_test.py') or file.endswith('_tests.py'):
                    file_abspath = os.path.join(project_path, relpath, file)
                    test_files_list.append(file_abspath)

    return test_files_list


if __name__ == '__main__':
    project_path = r'D:\CoursesResources\MasterThesis\Python_projects\spaCy\spacy'
    rel = r'sv'
    file = 'test_tokenizer.py'
    print(get_abspath(project_path, rel, file))

