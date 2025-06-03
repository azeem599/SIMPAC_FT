from F_Detector import mysql_handler as mh


def test_search_size_bigger_than():
    size = 30
    results = mh.search_size_bigger_than(size)
    print(len(results))
    for row in results:
        print(row[0], row[1], row[2])


def test_search_size_between():
    start = 10
    end = 30
    count = mh.search_size_between(start, end)
    print(count)


def test_search_test_smell():
    results = mh.search_test_smell()
    print(len(results))
    for r in results:
        test_case = r[0]
        path = r[1]
        count = r[2]
        print(test_case, path, count)


def test_smell_distribution():
    results = mh.smell_distribution()
    print(len(results))
    for r in results:
        smell_number = r[0]
        count = r[1]
        print(smell_number, count)


def test_search_file():
    project_path = r'D:\CoursesResources\MasterThesis\Python_projects\spaCy\spacy\tests'
    file = r'test_tokenizer.py'
    print(mh.search_file(project_path, file))

