import csv
import matplotlib.pyplot as plt
import mysql_handler as mh
from prettytable import PrettyTable
import click
import datetime
import os
from pathlib import Path
from changes_github import func_timer


def save_csv(file_path, headers, rows):
    with open(file_path, 'w', encoding='utf8', newline='') as f:
        f_csv = csv.writer(f)
        f_csv.writerow(headers)
        for row in rows:
            f_csv.writerow(row)
        print('save data to csv done!')


def combine_csv_path(folder, file_name):
    now = datetime.datetime.now()
    file_name = file_name + '_' + datetime.datetime.strftime(now, '%Y-%m-%d_%H-%M-%S') + '.csv'
    last_folder = Path(os.path.abspath(os.path.join(os.getcwd(), "..")))
    file_dir = last_folder / 'output' / 'csv' / folder
    if not os.path.exists(file_dir):
        os.mkdir(file_dir)
    file_path = file_dir / file_name
    return file_path


def combine_image_path(folder, image_name):
    now = datetime.datetime.now()
    file_name = image_name + '_' + datetime.datetime.strftime(now, '%Y-%m-%d_%H-%M-%S') + '.jpg'
    last_folder = Path(os.path.abspath(os.path.join(os.getcwd(), "..")))
    file_dir = last_folder / 'output' / 'image' / folder
    if not os.path.exists(file_dir):
        os.mkdir(file_dir)
    file_path = file_dir / file_name
    return file_path


def show_size():
    size = [[1, 9], [10, 19], [20, 29], [30, 39], [40, 49], [50, 59], [60, 69]]
    x_label = ['1-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '>=70']
    result = []
    for s in size:
        start = s[0]
        end = s[1]
        result.append(len(mh.search_size_between(start, end)))
    result.append(len(mh.search_size_bigger_than(69)))
    # x = range(result)
    name = "Test_Case_Size_Distribution"
    plt.ylabel("Count")
    plt.xlabel("Size")
    plt.title(name)
    plt.bar(x_label, result)
    for a, b in zip(x_label, result):
        plt.text(a, b + 1, '%.0f' % b, ha='center', va='bottom')
    image_path = combine_image_path('size', name)
    plt.savefig(image_path)
    print('save image done!')
    plt.show()


def show_size_bigger_than(size=30):
    results = mh.search_size_bigger_than(size)
    print("count: " + str(len(results)))
    headers = ['Test Case', 'Size', 'Path']
    file_name = 'size_bigger_than_' + str(size)
    file_path = combine_csv_path('size', file_name)
    save_csv(file_path, headers, results)
    table = PrettyTable(headers)
    for s in results:
        name = s[0]
        path = s[1]
        size = s[2]
        table.add_row([name, path, size])
    print(table)


def show_size_between(start=30, end=50):
    results = mh.search_size_between(start, end)
    print("count: " + str(len(results)))
    headers = ['Test Case', 'Size', 'Test Smells', 'Path']
    file_name = 'size_between_' + str(start) + '&' + str(end)
    file_path = combine_csv_path('size', file_name)
    save_csv(file_path, headers, results)
    table = PrettyTable(headers)
    for r in results:
        table.add_row([r[0], r[1], r[2], r[3]])
    print(table)


def show_smell():
    plt.figure(figsize=(10, 10))
    plt.figure(1)
    bar1 = plt.subplot(211)
    bar2 = plt.subplot(223)
    bar3 = plt.subplot(224)

    def show_smell_1():
        smells = len(mh.search_test_smell())
        no_smells = len(mh.search_no_smell())
        x_label = ["Test Cases with Smells", "Test Cases without Smells"]
        size = [smells, no_smells]
        bar1.set_title("Test Case Smell Distribution")
        color = ["blue", "green"]
        patches, l_text, p_text = bar1.pie(size, colors=color, labels=x_label, labeldistance=1.1,
                                           autopct="%1.1f%%", shadow=False, startangle=90, pctdistance=0.6)
        bar1.axis("equal")
        bar1.legend()

    def show_smell_2():
        result = mh.smell_distribution()
        x_label = []
        y_value = []
        for rt in result:
            x_label.append(str(rt[0]))
            y_value.append(rt[1])

        bar2.set_ylabel("Number of Test Cases")
        bar2.set_xlabel("Number of Smells")
        bar2.set_title("Test Smells Distribution")
        bar2.bar(x_label, y_value)
        for a, b in zip(x_label, y_value):
            bar2.text(a, b + 1, '%d' % b, ha='center', va='bottom')

    def show_smell_type():
        result = mh.smell_type()
        x_label = []
        y_value = []
        for rt in result:
            x_label.append(rt[0])
            y_value.append(rt[1])
        bar3.set_xlabel("Test Smell Type")
        bar3.set_ylabel("Count")
        bar3.set_title("Test Smells Type Distribution")
        bar3.bar(x_label, y_value)
        for a, b in zip(x_label, y_value):
            bar3.text(a, b + 1, '%d' % b, ha='center', va='bottom')

    folder = 'test_smell'
    results = mh.search_test_smell()
    headers = ['Test Case', 'Number of Smells', 'Path']
    file_name = 'test_smell_count'
    file_path = combine_csv_path(folder, file_name)
    save_csv(file_path, headers, results)
    table = PrettyTable(headers)
    print("count: " + str(len(results)))
    for r in results:
        table.add_row([r[0], r[1], r[2]])
    print(table)
    show_smell_1()
    show_smell_2()
    show_smell_type()
    image_path = combine_image_path(folder, 'Test_Smell_Distribution')
    plt.savefig(image_path)
    print('save image done!')
    plt.show()


def show_smell_details(test_case="all"):
    results = mh.search_smell_details(test_case)
    headers = ['Test Case', 'Number of Smells', 'Smell type', 'Tip', 'Location', 'Path']
    file_name = 'test_smell_details' + '__' + test_case
    file_path = combine_csv_path('test_smell', file_name)
    save_csv(file_path, headers, results)
    table = PrettyTable(headers)
    for r in results:
        table.add_row([r[0], r[1], r[2], r[3], r[4], r[5]])
    print(table)


def show_dependency_cover(days=3600):
    # dependency_cover_T = len(mh.search_dependency_cover_T(days))
    # git_diff_N = len(mh.search_git_diff_N(days))
    # dependency_cover_F = len(mh.search_dependency_cover_F(days))
    dependency_cover_F_count = mh.search_dependency_cover_F_count(days)

    #
    # def show_bar():
    #     x_label = ['dependency_cover_T', 'git_diff_N', 'dependency_cover_F&git_diff_Y']
    #     y_value = [dependency_cover_T, git_diff_N, dependency_cover_F]
    #     plt.xlabel("Dependency Coverage")
    #     plt.ylabel("Number of failed tests")
    #     plt.title("Dependency Coverage Distribution" + " (within " + str(days) + " days)")
    #     plt.bar(x_label, y_value)
    #     for a, b in zip(x_label, y_value):
    #         plt.text(a, b + 1, '%d' % b, ha='center', va='bottom')
    #     plt.show()

    def show_F_count():
        headers = ['Failed Test Case', 'NT-FDUC',
                   'Path', 'Latest Failed Build ID']
        file_name = 'Dependency_Cover'
        file_path = combine_csv_path('dependency_cover', file_name)
        save_csv(file_path, headers, dependency_cover_F_count)
        table = PrettyTable(headers)
        for r in dependency_cover_F_count:
            table.add_row([r[0], r[1], r[2], r[3]])
        print(table)

    show_F_count()
    # show_bar()


def show_latest_dependency_cover(build_id=0):
    results = mh.search_latest_failed_build(build_id)
    if len(results) > 0:
        data = []
        for r in results:
            temp = [r[0]]
            if r[2] == 'F':
                temp.append('Not Covered')
            else:
                temp.append('Covered')
            temp.append(r[3])
            temp.append(r[1])
            temp.append(r[4])
            temp.append(r[5])
            data.append(temp)
        headers = ['Failed Test', 'Coverage status', 'Previous State', 'Build ID', 'Build Finished Time', 'Path']
        file_name = results[0][1] + '_dependency_cover'
        file_path = combine_csv_path('dependency_cover', file_name)
        save_csv(file_path, headers, data)
        table = PrettyTable(headers)
        for r in data:
            table.add_row([r[0], r[1], r[2], r[3], r[4], r[5]])
        print(table)
    else:
        print('Build passed or build failed without failed tests or no such build')


def show_build_history(days=3600):
    failed_tests = mh.search_failed_times(days)
    build_status = mh.search_build_status(days)
    folder = 'build_history'

    def show_status():
        x_label = ['passed', 'failed without failed tests', 'failed with failed tests']
        y_value = []
        sum = 0
        for r in build_status:
            if r[0] == 2:
                sum += r[1]
            elif r[0] == 3 or r[0] == 4:
                continue
            else:
                y_value.append(r[1])
        y_value.append(sum)
        plt.xlabel("Status")
        plt.ylabel("Number of builds")
        plt.title("Build History Status Distribution" + " (within " + str(days) + " days)")
        plt.bar(x_label, y_value)
        for a, b in zip(x_label, y_value):
            plt.text(a, b + 1, '%d' % b, ha='center', va='bottom')

        image_path = combine_image_path(folder, "Build_History_Status_Distribution" + "(within_" + str(days) + "_days)")
        plt.savefig(image_path)

        plt.show()

    def show_failed_times():
        headers = ['Failed Test Name', 'Failed Times', 'Path']
        file_name = 'Test_Case_failed_times'
        file_path = combine_csv_path(folder, file_name)
        save_csv(file_path, headers, failed_tests)
        table = PrettyTable(['Failed Test Name', 'Failed Times', 'Path'])
        for r in failed_tests:
            table.add_row([r[0], r[1], r[2]])
        print(table)

    show_failed_times()
    show_status()


def show_flakiness_score_one(build_id):
    flakiness_list = mh.flakiness_score_one(build_id)
    headers = ['Build ID', 'Test Case', 'Score', 'NT-FDUC', 'Size', 'Number of Test Smells', 'Dependency Cover', 'Path']
    table = PrettyTable(headers)
    rows = []
    if flakiness_list:
        for f in flakiness_list:
            for k, v in f.items():
                temp = [v['build_id'], k, v['score'], v['failed_times'], v['size'], v['test_smells'],
                        v['dependency_cover'], v['path']]
                table.add_row(temp)
                rows.append(temp)
        folder = 'flakiness_score'
        file_name = 'Flakiness_Score_' + str(build_id)
        file_path = combine_csv_path(folder, file_name)
        save_csv(file_path, headers, rows)
        print(table.get_string(sortby="Score", reversesort=True))
    else:
        print('Build passed or build failed without failed tests or no such build')


def show_flakiness_score(test_case):
    results = mh.flakiness_score(test_case)
    score_dic = {}
    x_label = ['0', '0-1', '1-2', '2-3', '3-5', '5-7', '7-9', '>9']
    y_value = [0, 0, 0, 0, 0, 0, 0, 0]
    for r in results:
        score = r[1] * 0.2 + (r[2] - 29 if r[2] > 30 else 0) * 0.05 + r[3] * 0.4 + (2 if r[4] == 'F' else 0)
        if score == 0:
            y_value[0] += 1
        elif 0 < score <= 1:
            y_value[1] += 1
        elif 1 < score <= 2:
            y_value[2] += 1
        elif 2 < score <= 3:
            y_value[3] += 1
        elif 3 < score <= 5:
            y_value[4] += 1
        elif 5 < score <= 7:
            y_value[5] += 1
        elif 7 < score <= 9:
            y_value[6] += 1
        elif score > 9:
            y_value[7] += 1
        if score > 0:
            score = format(score, '.2f')
            score_dic[r[0]] = {'failed_times': r[1], 'size': r[2], 'test_smells': r[3], 'recent_cover': r[4],
                               'git_diff': r[5], 'build_id': r[6], 'path': r[7], 'score': score}
    plt.xlabel("Flakiness Score")
    plt.ylabel("Number of Test Cases")
    plt.title("Flakiness Score Distribution")
    plt.bar(x_label, y_value)
    for a, b in zip(x_label, y_value):
        plt.text(a, b + 1, '%d' % b, ha='center', va='bottom')

    headers = ['Test Case', 'Score', 'NT-FDUC', 'Size', 'Number of Test Smells', 'Latest Dependency Cover',
               'Latest Failed build_id', 'Path']
    table = PrettyTable(headers)

    rows = []
    for key, value in score_dic.items():
        temp = [key, value['score'], value['failed_times'], value['size'], value['test_smells'], value['recent_cover'],
                value['build_id'], value['path']]
        table.add_row(temp)
        rows.append(temp)

    folder = 'flakiness_score'
    file_name = 'Flakiness_Score'
    file_path = combine_csv_path(folder, file_name)
    save_csv(file_path, headers, rows)
    print(table.get_string(sortby="Score", reversesort=True))

    image_path = combine_image_path(folder, "Flakiness_Score_Distribution")
    plt.savefig(image_path)

    plt.show()


@func_timer
def show_flakiness():
    results = mh.search_flakiness()
    headers = ['Build ID', 'Test Method', 'Flaky or Not', 'Detection Method', 'Traceback Coverage', 'Number of Smells',
               'Flaky Frequency', 'Size', 'Path']
    rows = []
    table = PrettyTable(headers)
    for res in results:
        if res[3] == 'T':
            method = 'Traceback Coverage'
        else:
            method = 'Multi-Factor'

        if res[4] == 'T':
            cover = 'Covered'
        else:
            cover = 'Not Covered'

        if res[7] == 0:
            smells = 'Unavailable'
            size = 'Unavailable'
            temp = [res[0], res[1], 'flaky', method, cover, smells, res[6], size, res[8]]
        else:
            temp = [res[0], res[1], 'flaky', method, cover, res[5], res[6], res[7], res[8]]

        table.add_row(temp)
        rows.append(temp)

    folder = 'flakiness_detection'
    file_name = 'Flakiness_Detection'
    file_path = combine_csv_path(folder, file_name)
    save_csv(file_path, headers, rows)
    print(table[:500])


def show_detection_results():
    results = mh.search_detection_results()
    headers = ['Build ID', 'Test Method', 'Flaky or Not', 'Detection Method', 'Traceback Cover',
               'Number of Smells', 'Flaky Frequency', 'Size', 'Path']
    rows = []
    table = PrettyTable(headers)
    x_label = ['TC_flaky', 'TC_non-flaky', 'MF_flaky', 'MF_non-flaky', 'Missing']
    TC_flaky = mh.search_TC_flaky()
    TC_non_flaky = mh.search_TC_non_flaky()
    MF_flaky = mh.search_MF_flaky()
    MF_non_flaky = mh.search_MF_non_flaky()
    Missing = mh.search_missing_factors()
    y_value = [TC_flaky, TC_non_flaky, MF_flaky, MF_non_flaky, Missing]

    plt.xlabel("Results")
    plt.ylabel("Number of Tests")
    plt.title("Detection Results")
    plt.bar(x_label, y_value)
    for a, b in zip(x_label, y_value):
        plt.text(a, b + 1, '%d' % b, ha='center', va='bottom')

    for res in results:
        if res[3] == 'T':
            method = 'Traceback Coverage'
        else:
            method = 'Multi-Factor'

        if res[2] == 'F':
            dr = 'Flaky'
        elif res[2] == 'N':
            dr = 'Non-Flaky'
        else:
            dr = 'Missing factors'

        if res[4] == 'T':
            cover = 'Covered'
        else:
            cover = 'Not Covered'

        if res[7] == 0:
            smells = 'Unavailable'
            size = 'Unavailable'
            temp = [res[0], res[1], dr, method, cover, smells, res[6], size, res[8]]
        else:
            temp = [res[0], res[1], dr, method, cover, res[5], res[6], res[7], res[8]]

        table.add_row(temp)
        rows.append(temp)

    folder = 'results'
    file_name = 'Results'
    file_path = combine_csv_path(folder, file_name)
    save_csv(file_path, headers, rows)
    print(table[:500])

    image_path = combine_image_path(folder, "Results")
    plt.savefig(image_path)

    plt.show()


@func_timer
def show_detection_results_id(build_id):
    results = mh.search_detection_result_id(build_id)
    headers = ['Build ID', 'Test Method', 'Flaky or Not', 'Detection Method', 'Traceback Cover',
               'Number of Smells', 'Flaky Frequency', 'Size', 'Path']
    table = PrettyTable(headers)
    rows = []
    if len(results) > 0:
        print(len(results), 'failed tests')
        for res in results:
            if res[3] == 'T':
                method = 'Traceback Coverage'
            else:
                method = 'Multi-Factor'

            if res[2] == 'F':
                dr = 'Flaky'
            elif res[2] == 'N':
                dr = 'Non-Flaky'
            else:
                dr = 'Missing factors'

            if res[4] == 'T':
                cover = 'Covered'
            else:
                cover = 'Not Covered'

            if res[7] == 0:
                smells = 'Unavailable'
                size = 'Unavailable'
                temp = [res[0], res[1], dr, method, cover, smells, res[6], size, res[8]]
            else:
                temp = [res[0], res[1], dr, method, cover, res[5], res[6], res[7], res[8]]

            table.add_row(temp)
            rows.append(temp)
        folder = 'results_id'
        file_name = str(build_id)
        file_path = combine_csv_path(folder, file_name)
        save_csv(file_path, headers, rows)
        print(table)
    else:
        print("No such build in DB!")


@func_timer
def show_detection_results_test(test_method):
    results = mh.search_detection_result_test(test_method)
    headers = ['Build ID', 'Test Method', 'Flaky or Not', 'Detection Method', 'Traceback Cover',
               'Number of Smells', 'Flaky Frequency', 'Size', 'Path']
    table = PrettyTable(headers)
    rows = []
    if len(results) > 0:
        print(len(results), 'failed builds')
        for res in results:
            if res[3] == 'T':
                method = 'Traceback Coverage'
            else:
                method = 'Multi-Factor'

            if res[2] == 'F':
                dr = 'Flaky'
            elif res[2] == 'N':
                dr = 'Non-Flaky'
            else:
                dr = 'Missing factors'

            if res[4] == 'T':
                cover = 'Covered'
            else:
                cover = 'Not Covered'

            if res[7] == 0:
                smells = 'Unavailable'
                size = 'Unavailable'
                temp = [res[0], res[1], dr, method, cover, smells, res[6], size, res[8]]
            else:
                temp = [res[0], res[1], dr, method, cover, res[5], res[6], res[7], res[8]]

            table.add_row(temp)
            rows.append(temp)
        folder = 'results_test'
        file_name = test_method
        file_path = combine_csv_path(folder, file_name)
        save_csv(file_path, headers, rows)
        print(table)
    else:
        print("No such test in DB!")


@click.command()
@click.option('--type', type=click.Choice(['size', 'size_bigger_than', 'size_between', 'smell', 'smell_details',
                                           'tc_all', 'tc_one', 'test_history', 'flaky', 'results',
                                           'results_id', 'results_test']),
              help='the type of data that you want to check')
@click.option('--size', type=int, help='you need set size when you choose size_bigger_than')
@click.option('--between', nargs=2, type=int, help='you need set start and end when you choose size_between')
@click.option('--test', default='all',
              help='get test smell details of a test case(default:all) when '
                   'you choose smell_details, all means show the details of all the test cases')
@click.option('--days', type=int, default=3600,
              help='get the data generated within x days(default:3600),'
                   'you can set days when you choose dependency_cover or build_history')
@click.option('--id', type=int, default=0,
              help='build id')
def main(type, size, between, test, days, id):
    if between is None:
        between = [30, 50]
    if type == 'size':
        show_size()
    elif type == 'size_bigger_than':
        show_size_bigger_than(size=size)
    elif type == 'size_between':
        show_size_between(between[0], between[1])
    elif type == 'smell':
        show_smell()
    elif type == 'smell_details':
        show_smell_details(test)
    elif type == 'tc_all':
        show_dependency_cover(days)
    elif type == 'test_history':
        show_build_history(days)
    elif type == 'tc_one':
        show_latest_dependency_cover(id)
    elif type == 'flaky':
        show_flakiness()
    elif type == 'results':
        show_detection_results()
    elif type == 'results_id':
        show_detection_results_id(id)
    elif type == 'results_test':
        show_detection_results_test(test)


if __name__ == '__main__':
    main()
