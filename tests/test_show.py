from F_Detector import show


def test_show_size():
    show.show_size()


def test_show_size_bigger_than():
    show.show_size_bigger_than(30)


def test_show_size_between():
    show.show_size_between(30, 50)


def test_show_smell():
    show.show_smell()


def test_show_smell_type():
    show.show_smell().show_smell_type()


def test_show_smell_details():
    test_case2 = "test_urls"
    show.show_smell_details()


def test_show_dependency_cover():
    days = 1080
    show.show_dependency_cover(days)


def test_show_latest():
    build_id = 675313645
    show.show_latest_dependency_cover(build_id)


def test_show_build_history():
    days = 1080
    show.show_build_history()


def test_show_flakiness_score():
    show.show_flakiness_score('all')


def test_show_flakiness_score_one():
    build_id = 0
    show.show_flakiness_score_one(build_id)
