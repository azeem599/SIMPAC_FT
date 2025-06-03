# from F_Detector.auto_evaluate import *
#
#
# def test_checkout_commit():
#     commit = '7b33b2854f99ef531d72e19e6dda773f43a5fe13'
#     project_path = r'D:\CoursesResources\MasterThesis\Python_projects\spaCy'
#     res = checkout_commit(commit, project_path)
#     if res == 0:
#         print("SSSS")
#     else:
#         print("FFFF")
#
#
# def test_rerun_tests_spacy():
#     commit = '7b33b2854f99ef531d72e19e6dda773f43a5fe13'
#     project_path = r'D:\CoursesResources\MasterThesis\Python_projects\spaCy'
#     rerun_tests_spacy(project_path)
#


def F(name):
    Sam = ['Sam', 11, 'male']
    Lisa = ['Lisa', 13, 'female']
    if name == 'Sam':
        return Sam[1]
    elif name == 'Lisa':
        return Lisa[1]
    else:
        return -1
def test_A():
    test_name = ['Sam', 'Jay']
    for name in test_name:
        print(F(name))


def divide(x, y):
    return x / y


def test_divide():
    x = 10
    y = 0
    divide(x, y)
