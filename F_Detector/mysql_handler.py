import datetime
import os
import re
import subprocess
import time
import traceback
from path_process import get_abspath

import pymysql
import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from get_test_smells import get_test_smell_project, get_size_file, get_test_size, get_test_smell_method
from trace_cover import get_compare, diff_compare
from changes_github import get_changes, func_timer


def connect(host="localhost", user="root", pw="root", db="spaCy"):
    return pymysql.connect(host, user, pw, db)  # url,username,password,database


# create tables
def create_tables():
    db = connect()
    cur = db.cursor()
    cur.execute("drop table if exists build_history")
    cur.execute("drop table if exists test_smells")
    cur.execute("drop table if exists test_cases")
    cur.execute("drop table if exists failed_tests")
    cur.execute("drop table if exists total_builds")
    print("creating tables......")
    try:
        create_build_history = """CREATE TABLE build_history(
                                ID INT NOT NULL AUTO_INCREMENT  COMMENT 'id' ,
                                BUILD_ID VARCHAR(64) NOT NULL   COMMENT 'build_id' ,
                                BRANCH VARCHAR(128)    COMMENT 'branch' ,
                                DURATION VARCHAR(64)    COMMENT 'duration' ,
                                CREATED_TIME DATETIME    COMMENT 'CREATED_TIME' ,
                                STATUS INT   COMMENT 'status 0: passed; 1: failed; 2: failed with failed tests; 3: erroed; 4: canceled' ,
                                PREVIOUS_STATE VARCHAR(32)    COMMENT 'previous_state' ,
                                COMMIT_SHA VARCHAR(128)    COMMENT 'commit_sha' ,
                                PRIMARY KEY (ID)
                            )"""
        create_test_smells = """CREATE TABLE test_smells(
                                ID INT NOT NULL AUTO_INCREMENT  COMMENT 'id' ,
                                TEST_CASE_NAME VARCHAR(128)    COMMENT 'test_case_name' ,
                                TEST_SMELL_TYPE VARCHAR(32)    COMMENT 'test_smell_type' ,
                                TIP VARCHAR(64)    COMMENT 'tip' ,
                                LOCATION INT    COMMENT 'test_smell_location' ,
                                CREATED_TIME DATETIME    COMMENT 'CREATED_TIME' ,
                                UPDATED_TIME DATETIME    COMMENT 'UPDATED_TIME' ,
                                PATH VARCHAR(512)    COMMENT 'path' ,
                                PRIMARY KEY (ID)
                            )"""
        create_test_cases = """CREATE TABLE test_cases(
                                ID INT NOT NULL AUTO_INCREMENT  COMMENT 'id' ,
                                NAME VARCHAR(128)    COMMENT 'test_case_name' ,
                                PATH VARCHAR(512)    COMMENT 'PATH' ,
                                SIZE INT  DEFAULT 0  COMMENT 'size' ,
                                TEST_SMELLS INT  DEFAULT 0  COMMENT 'test_smell_number' ,
                                CREATED_TIME DATETIME    COMMENT 'CREATED_TIME' ,
                                UPDATED_TIME DATETIME    COMMENT 'UPDATED_TIME' ,
                                ML_SCORE DECIMAL(4,2)  DEFAULT 0  COMMENT 'ML_score machine_learning score
                            Reserved Field' ,
                                PRIMARY KEY (ID)
                            )"""
        create_failed_tests = """CREATE TABLE failed_tests(
                                ID INT NOT NULL AUTO_INCREMENT  COMMENT 'id' ,
                                BUILD_ID VARCHAR(64) NOT NULL   COMMENT 'build_id build_history_fk' ,
                                FAILED_TEST_NAME VARCHAR(128) NOT NULL   COMMENT 'failed_test_name test_cases_fk' ,
                                DETECTION_RESULT VARCHAR(1) COMMENT 'detection result, F means flaky, N means not flaky, M means miss factors(smells and size)',
                                DETECTION_METHOD VARCHAR(1) COMMENT 'detection method(T means Traceback coverage, M means multi-factor)',
                                STATEMENT_COVER VARCHAR(1)    COMMENT 'statement coverage' ,
                                FILE_COVER VARCHAR(1)         COMMENT 'file coverage',
                                GIT_DIFF VARCHAR(1)     COMMENT 'successfully got diff from github? Y(yes) or N(not) ',
                                PREVIOUS_STATE INT DEFAULT 0 COMMENT 'previous state of the failed test',
                                SMELLS INT default 0   COMMENT 'number of test smells',
                                FLAKY_FREQUENCY DECIMAL(4,2)    COMMENT 'flaky frequency' ,
                                SIZE INT default 0    COMMENT 'test size',
                                CREATED_TIME DATETIME    COMMENT 'created_time' ,
                                PATH VARCHAR(512)    COMMENT 'path' ,
                                PRIMARY KEY (ID)
                            )"""
        # create_total_builds = """CREATE TABLE total_builds(
        #                         total INT NOT NULL   COMMENT 'total_builds' ,
        #                         passed INT    COMMENT 'passed_builds' ,
        #                         failed INT    COMMENT 'failed_builds' ,
        #                         failed_test INT    COMMENT 'failed_test_builds' ,
        #                         PRIMARY KEY (total)
        #                     )"""
        cur.execute(create_build_history)
        cur.execute(create_test_cases)
        cur.execute(create_failed_tests)
        cur.execute(create_test_smells)
        # cur.execute(create_total_builds)
        db.commit()
        print("tables created!")
    except Exception as e:
        print("operation error: " + str(e))
        print(traceback.format_exc())
        db.rollback()
        print("rollback!")
    finally:
        cur.close()
        db.close()


def save_case_and_smells(project_path):
    t1 = time.time()
    db = connect()
    t2 = time.time()

    print("getting test smells......")
    project_smells = get_test_smell_project(project_path)
    t3 = time.time()
    print("get test smells succeed, cost " + str(t3 - t2) + " seconds")

    cur = db.cursor()
    test_file_number = 0
    test_smell_number = 0
    test_case_number = 0
    print("save data into db......")
    try:
        for file_path, smells in project_smells.items():
            size_dic = get_size_file(file_path)
            # save test case size
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            test_file_number += 1
            file_path = file_path.replace("\\", "\\\\")
            for test, size in size_dic.items():
                test_case_number += 1
                save_size = "INSERT IGNORE INTO test_cases(NAME,PATH,SIZE,CREATED_TIME) \
                                values ('%s','%s','%d','%s')" % (test, file_path, size, dt)
                cur.execute(save_size)

            # update test smells
            dt2 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            for smell in smells:
                if smell:
                    for name, smell_list in smell.items():
                        num = 0  # test smell number
                        for sm in smell_list:
                            num += len(sm[3])
                            # insert test smells into table test_smells
                            for location in sm[3]:
                                test_smell_number += 1
                                save_smells = "INSERT IGNORE INTO test_smells(TEST_CASE_NAME,TEST_SMELL_TYPE,TIP,LOCATION," \
                                              "PATH," \
                                              "CREATED_TIME) values ('%s','%s','%s','%d','%s','%s')" % (
                                                  name, sm[0], sm[1], location, file_path, dt2)
                                cur.execute(save_smells)
                        # update test smell number of table test_cases
                        save_smell_number = "UPDATE test_cases SET TEST_SMELLS='%d' " \
                                            "WHERE NAME='%s' and PATH='%s'" % (num, name, file_path)
                        cur.execute(save_smell_number)
        db.commit()
        t4 = time.time()
        print("save data done!")
        print("detect and save " + str(test_file_number) + " test files")
        print("detect and save " + str(test_case_number) + " test cases")
        print("detect and save " + str(test_smell_number) + " test smells")
        print("cost " + str(t4 - t3) + "seconds")
        print("total cost: " + str(t4 - t1) + " seconds")
    except Exception as e:
        print("operation error: " + str(e))
        print(traceback.format_exc())
        db.rollback()
        print("rollback!")
    finally:
        cur.close()
        db.close()


def save_passed_builds(passed_builds_list):
    db = connect()
    cur = db.cursor()
    print("db connected!")
    print("saving passed builds into db......")
    t1 = time.time()
    try:
        # delete_history = "truncate table build_history"
        # cur.execute(delete_history)
        for build in passed_builds_list:
            if build['branch_name']:
                duration = str(datetime.timedelta(seconds=build['duration']))
                UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
                utc_time = datetime.datetime.strptime(build['finished_at'], UTC_FORMAT)
                status = 0
                if build['state'] == 'errored':
                    status = 3
                elif build['state'] == 'canceled':
                    status = 4
                save_builds = "INSERT IGNORE INTO build_history(build_id, branch, duration, created_time, status, PREVIOUS_STATE,commit_sha) " \
                              "VALUES ('%s','%s','%s','%s','%s','%s','%s')" % (
                                  str(build['id']), build['branch_name'], duration,
                                  utc_time, status, str(build['previous_state']), str(build['commit_sha']))
                # print(save_builds)
                cur.execute(save_builds)
        db.commit()
        t2 = time.time()
        print("save passed builds done!")
        print("cost " + str(t2 - t1) + "seconds")
    except Exception as e:
        db.rollback()
        print("error: " + str(e))
        print(traceback.format_exc())
        print("rollback!")
    finally:
        cur.close()
        db.close()


def save_failed_builds_and_tests(failed_build_list, failed_test_dic):
    db = connect()
    cur = db.cursor()
    print("db connected!")
    print("saving failed builds into db......")
    t1 = time.time()
    try:
        # delete_tests = "truncate table failed_tests"
        # cur.execute(delete_tests)
        # save failed builds
        for build in failed_build_list:
            if build['branch_name']:
                duration = str(datetime.timedelta(seconds=build['duration']))
                UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
                utc_time = datetime.datetime.strptime(build['finished_at'], UTC_FORMAT)
                status = 1
                save_builds = "INSERT IGNORE INTO build_history(build_id, branch, duration, created_time, status,PREVIOUS_STATE, commit_sha) " \
                              "values ('%s','%s','%s','%s','%d','%s','%s')" % (
                                  build['id'], build['branch_name'], duration,
                                  utc_time, status, str(build['previous_state']), build['commit_sha'])
                cur.execute(save_builds)
        db.commit()

        t2 = time.time()
        print("save failed builds done!")
        print("cost " + str(t2 - t1) + "seconds")
        print("\n\n")
        print("saving failed tests into db......")
        # save failed tests
        count = 1
        for build_id, failed_test in failed_test_dic.items():
            print("processing " + str(count) + " " + "build id: " + build_id)
            update_status = "update build_history set STATUS=2 where BUILD_ID='%s'" % build_id
            cur.execute(update_status)  # update build status to failed with failed tests
            get_time = "select CREATED_TIME from build_history where BUILD_ID='%s'" % build_id
            cur.execute(get_time)
            created_time = cur.fetchall()[0][0]
            count += 1
            compare_sha = get_compare(failed_test['compare_url'])
            # if not compare_url
            if '...' not in compare_sha and not re.findall('^\\d+$', compare_sha):
                compare_sha = failed_test['commit_sha']
            change_dic = get_changes(compare_sha, failed_test['slug'])
            diff_dic = diff_compare(change_dic, failed_test['traceback'])
            if failed_test['failed_tests']:
                for test in failed_test['failed_tests']:
                    path = test['test_dir'] + test['test_file']
                    path.replace('\'', '')
                    test_name = test['test_case']
                    if diff_dic['diff'] == 'Y':
                        statement_cover = diff_dic[test_name]['statement']
                        file_cover = diff_dic[test_name]['file']
                    else:
                        statement_cover = 'U'
                        file_cover = 'U'
                    save_failed_tests = "insert IGNORE into failed_tests(build_id, failed_test_name, path, statement_cover, file_cover, git_diff,created_time) VALUES " \
                                        "('%s','%s','%s','%s','%s','%s','%s')" % (
                                            build_id, test_name, pymysql.escape_string(path), statement_cover,
                                            file_cover, diff_dic['diff'], created_time)
                    cur.execute(save_failed_tests)
        t3 = time.time()
        db.commit()
        print("save failed tests done!")
        print("cost " + str(t3 - t2) + "seconds")

    except Exception as e:
        db.rollback()
        print("error: " + str(e))
        print(traceback.format_exc())
        print("rollback!")

    finally:
        cur.close()
        db.close()


def update_flakiness_possibility():
    db = connect()
    cur = db.cursor()


def search(sql):
    db = connect()
    cur = db.cursor()
    results = []
    try:
        cur.execute(sql)
        results = cur.fetchall()
    except Exception as e:
        print(e)
    finally:
        cur.close()
        db.close()
        return results


def get_failed_test(test_case):
    sql = """select failed_test_name from failed_tests where failed_test_name='%s'""" % test_case
    return search(sql)


def get_failed_times(test_case, created_time):
    sql = """SELECT COUNT(failed_test_name) AS failed_times FROM failed_tests
             WHERE FAILED_TEST_NAME='%s' and created_time<'%s'""" % (test_case, created_time)
    return search(sql)


def get_build_created_time(build_id):
    sql = """select created_time from build_history where build_id='%s'""" % build_id
    return search(sql)


def get_build_pre_state(build_id):
    sql = """select previous_state from build_history where build_id='%s'""" % build_id
    return search(sql)


def get_parent_failed_tests(build_id):
    sql = """SELECT failed_test_name FROM failed_tests WHERE build_id='%s'""" % build_id
    return search(sql)


def get_parent_build(parent_commit, created_time):
    sql = """SELECT build_id,status,previous_state FROM build_history bh WHERE commit_sha='%s'
             AND bh.`CREATED_TIME`<'%s'
             ORDER BY '%s'-bh.`CREATED_TIME` LIMIT 1""" % (parent_commit, created_time, created_time)
    return search(sql)


def search_parent_commit(build_id):
    sql = """SELECT parent_commit_1,parent_commit_2 FROM build_history
             WHERE build_id='%s'""" % build_id
    return search(sql)


def search_all_failed_tests():
    sql = 'select build_id,failed_test_name,created_time from failed_tests'
    return search(sql)


# factor 1: test case size
def search_size_bigger_than(size):
    sql = "SELECT tc.`NAME`, `size`, path FROM test_cases tc WHERE `size`>%s order by size desc " % size
    return search(sql)


def search_size_between(start, end):
    sql = "SELECT `NAME`,`SIZE`,`TEST_SMELLS`,`PATH` FROM test_cases " \
          "WHERE `SIZE` BETWEEN %s AND %s order by `SIZE` desc " % (start, end)
    return search(sql)


# factor 2: test smell
def search_test_smell():
    sql = """SELECT `NAME`,test_smells AS test_smell_number,PATH 
             FROM test_cases 
             WHERE test_smells>0 
             ORDER BY test_smell_number DESC"""
    return search(sql)


def search_smell_size(test_name):
    sql = """SELECT test_smells, `size`
             FROM test_cases 
             WHERE `name`='%s' """ % test_name
    return search(sql)


def search_smell_details(test_case):
    if test_case == "all":
        sql = """SELECT `NAME`, tc.`TEST_SMELLS`,ts.`TEST_SMELL_TYPE`,ts.`TIP`,ts.`LOCATION`,tc.`PATH`
                 FROM test_cases tc,test_smells ts 
                 WHERE tc.`NAME`=ts.`TEST_CASE_NAME`
                 ORDER BY tc.`TEST_SMELLS` DESC"""
        return search(sql)
    else:
        sql = """SELECT `NAME`, tc.`TEST_SMELLS`,ts.`TEST_SMELL_TYPE`,ts.`TIP`,ts.`LOCATION`,tc.`PATH`
                 FROM test_cases tc,test_smells ts 
                 WHERE tc.`NAME`=ts.`TEST_CASE_NAME` and tc.`NAME`='%s'""" % test_case
        return search(sql)


def search_previous_state(build_id):
    sql = """select previous_state from build_history
             where build_id='%s'""" % build_id
    return search(sql)


def search_flaky_frequency(failed_test, build_id):
    sql = """select flaky_frequency from failed_tests
             where failed_test_name='%s' and build_id='%s'""" % (failed_test, build_id)
    return search(sql)


def search_test_path(failed_test):
    sql = """select path from test_case
             where `name`='%s'""" % failed_test
    return search(sql)


def search_no_smell():
    sql = """SELECT * FROM test_cases WHERE test_smells=0"""
    return search(sql)


def smell_distribution():
    sql = """SELECT test_smells,COUNT(test_smells) AS test_smell_count 
             FROM test_cases GROUP BY test_smells ORDER BY test_smells"""
    return search(sql)


def smell_type():
    sql = """SELECT TEST_SMELL_TYPE,COUNT(*) FROM test_smells GROUP BY TEST_SMELL_TYPE"""
    return search(sql)


# factor 3: dependency coverage
def search_dependency_cover_T(days):
    sql = """SELECT FAILED_TEST_NAME 
             FROM failed_tests 
             WHERE FILE_COVER='T' and DATE_SUB(CURDATE(),INTERVAL %d DAY) <=CREATED_TIME""" % days
    return search(sql)


def search_git_diff_N(days):
    sql = """SELECT FAILED_TEST_NAME 
             FROM failed_tests 
             WHERE git_diff='N' and DATE_SUB(CURDATE(),INTERVAL %d DAY) <=CREATED_TIME""" % days
    return search(sql)


def search_dependency_cover_F(days):
    sql = """SELECT FAILED_TEST_NAME 
             FROM failed_tests 
             WHERE STATEMENT_COVER="F" AND FILE_COVER="F" AND DATE_SUB(CURDATE(),INTERVAL %d DAY) <=CREATED_TIME""" % days
    return search(sql)


def search_dependency_cover_F_count(days):
    sql = """SELECT FAILED_TEST_NAME,COUNT(FAILED_TEST_NAME) AS times,path,build_id AS last_build
             FROM failed_tests 
             WHERE STATEMENT_COVER='F'  and previous_state='passed' AND DATE_SUB(CURDATE(),INTERVAL %d DAY) <=CREATED_TIME
             GROUP BY FAILED_TEST_NAME 
             ORDER BY times DESC""" % days
    return search(sql)


def search_latest_failed_build(build_id):
    if build_id == 0:
        sql = """SELECT ft.FAILED_TEST_NAME,ft.build_id,ft.STATEMENT_COVER, bh.previous_state,
                 ft.created_time, ft.path 
                 FROM failed_tests ft join build_history bh
                 on ft.build_id = bh.build_id
                 WHERE ft.build_id = (SELECT build_id FROM build_history 
                 WHERE STATUS=2 ORDER BY CREATED_TIME DESC LIMIT 1)"""
    else:
        sql = """SELECT ft.FAILED_TEST_NAME,ft.build_id,ft.STATEMENT_COVER, bh.previous_state,
                 ft.created_time, ft.path 
                 FROM failed_tests ft join build_history bh
                 on ft.build_id = bh.build_id
                 WHERE ft.build_id = %d""" % build_id
    return search(sql)


# factor 4: build history
def search_failed_times(days):
    sql = """SELECT FAILED_TEST_NAME,COUNT(*) AS failed_times, path
             FROM failed_tests 
             WHERE DATE_SUB(CURDATE(),INTERVAL %d DAY) <=CREATED_TIME
             GROUP BY FAILED_TEST_NAME 
             HAVING failed_times>0
             ORDER BY failed_times DESC""" % days
    return search(sql)


def search_build_status(days):
    sql = """SELECT `status` ,COUNT(*) AS times 
             FROM build_history 
             WHERE DATE_SUB(CURDATE(),INTERVAL %d DAY) <=CREATED_TIME
             GROUP BY `status`""" % days
    return search(sql)


# flakiness score
def flakiness_score(test_case):
    if test_case == 'all':
        sql = """SELECT tc.`NAME`,COUNT(ft.`FAILED_TEST_NAME`) AS failed_times,tc.`SIZE`,tc.`TEST_SMELLS`, 
                 ft.`STATEMENT_COVER` AS recent_cover, ft.git_diff,ft.`BUILD_ID` AS recent_failed_build_id,ft.`PATH`
                 FROM test_cases tc LEFT JOIN (SELECT * FROM failed_tests WHERE STATEMENT_COVER='F' AND FILE_COVER='F') ft 
                 ON tc.`NAME`=ft.`FAILED_TEST_NAME`
                 GROUP BY tc.`NAME`
                 ORDER BY failed_times DESC"""
    else:
        sql = """SELECT tc.`NAME`,COUNT(ft.`FAILED_TEST_NAME`) AS failed_times,tc.`SIZE`,tc.`TEST_SMELLS`, 
                 ft.`STATEMENT_COVER` AS recent_cover, ft.git_diff,ft.`BUILD_ID` AS recent_failed_build_id,ft.`PATH`
                 FROM test_cases tc right JOIN (SELECT * FROM failed_tests WHERE STATEMENT_COVER='F' AND FILE_COVER='F') ft 
                 ON tc.`NAME`=ft.`FAILED_TEST_NAME`
                 where ft.`FAILED_TEST_NAME` = '%s'
                 GROUP BY tc.`NAME`
                 ORDER BY failed_times DESC""" % test_case
    return search(sql)


def search_flakiness():
    sql = """select build_id, failed_test_name, detection_result, detection_method, statement_cover,
             smells, flaky_frequency, `size`, path
             from failed_tests where detection_result='F'
             order by detection_method desc"""
    return search(sql)


def search_detection_results():
    sql = """select build_id, failed_test_name, detection_result, detection_method, statement_cover,
             smells, flaky_frequency, `size`, path
             from failed_tests"""
    return search(sql)


def search_detection_result_id(build_id):
    sql = """select build_id, failed_test_name, detection_result, detection_method, statement_cover,
             smells, flaky_frequency, `size`, path
             from failed_tests
             where build_id='%s'""" % build_id
    return search(sql)


def search_detection_result_test(test_method):
    sql = """select build_id, failed_test_name, detection_result, detection_method, statement_cover,
             smells, flaky_frequency, `size`, path
             from failed_tests
             where failed_test_name='%s'""" % test_method
    return search(sql)


def search_latest_build_created_time():
    sql = """select created_time from build_history
              order by created_time desc
              limit 1"""
    return search(sql)


def search_factors(build_id, test_method):
    sql = """select flaky_frequency, statement_cover, smells, previous_state, `size`
             from failed_tests
             where build_id='%s' and failed_test_name='%s'""" % (build_id, test_method)
    return search(sql)


def search_TC_flaky():
    sql = """select count(*)
             from failed_tests
             where detection_result='F' and detection_method='T'"""
    return search(sql)[0][0]


def search_TC_non_flaky():
    sql = """select count(*)
             from failed_tests
             where detection_result='N' and detection_method='T'"""
    return search(sql)[0][0]


def search_MF_flaky():
    sql = """select count(*)
             from failed_tests
             where detection_result='F' and detection_method='M'"""
    return search(sql)[0][0]


def search_MF_non_flaky():
    sql = """select count(*)
             from failed_tests
             where detection_result='N' and detection_method='M'"""
    return search(sql)[0][0]


def search_missing_factors():
    sql = """select count(*)
             from failed_tests
             where detection_result='M'"""
    return search(sql)[0][0]


def flakiness_score_one(build_id):
    failed_tests = search_latest_failed_build(build_id)
    flakiness_list = []
    if failed_tests:
        for f in failed_tests:
            score_dic = {}
            r = flakiness_score(f[0])
            if r:
                size_score = 0
                smell_score = 0
                if r[0][2]:
                    size_score = r[0][2] - 29 if r[0][2] > 30 else 0
                if r[0][3]:
                    smell_score = r[0][3] * 0.4
                score = r[0][1] * 0.2 + size_score + smell_score + (2 if r[0][4] == 'F' else 0)
                score_dic[f[0]] = {'failed_times': r[0][1], 'size': r[0][2], 'test_smells': r[0][3],
                                   'dependency_cover': f[1], 'build_id': f[2], 'path': r[0][7], 'score': score}
                flakiness_list.append(score_dic)

    return flakiness_list


@func_timer
def update_flaky_frequency(start_time='2000-01-01 00:00:00'):
    db = connect()
    cur = db.cursor()
    sql_1 = """select build_id, failed_test_name,created_time 
               from failed_tests 
               where created_time>'%s'
               order by created_time desc""" % start_time
    all_failed_tests = search(sql_1)
    try:
        for test in all_failed_tests:
            sql_2 = """select build_id, created_time from failed_tests
                       where failed_test_name='%s' and created_time<='%s'
                       order by created_time""" % (test[1], test[2])
            failed_history = search(sql_2)
            failed_count = len(failed_history)
            temp = failed_history[0][1]
            transitions = 1
            for fh in failed_history:
                if temp + datetime.timedelta(hours=8) < fh[1]:
                    transitions += 1
                temp = fh[1]

            # print(test[0], test[1], transitions, failed_count, float(transitions / (failed_count+2)))
            flaky_frequency = round(transitions / (failed_count + 2), 2)
            # print(flaky_frequency)
            update = """update failed_tests 
                        set flaky_frequency='%s'
                        where build_id='%s' and failed_test_name='%s'""" % (flaky_frequency, test[0], test[1])
            cur.execute(update)

    except Exception as e:
        db.rollback()
        print("error: " + str(e))
        print(traceback.format_exc())
        print("rollback!")

    finally:
        db.commit()
        cur.close()
        db.close()


def checkout_commit(commit_sha, project_path):
    # os.chdir(project_path)
    command = 'git checkout ' + commit_sha
    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                              cwd=project_path, stderr=subprocess.PIPE)
    output = result.stdout.readlines()
    return output


def read_data(data_path):
    data = pd.read_csv(data_path, header=1)
    data_array = np.array(data)
    x_data = np.array(data_array[1:, 2:7], dtype=int)
    y_target = np.array(data_array[1:, 7:8], dtype=int)
    y_target = y_target.ravel()

    return x_data, y_target


def KNN_predict(data, factors):
    x_data, y_target = read_data(data)
    knn = KNeighborsClassifier(10, p=1)
    knn.fit(x_data, y_target)
    predict = knn.predict(factors)
    probility = knn.predict_proba(factors)[0]
    # [1]
    # [0.1 0.9]
    return predict, probility


def search_file(project_path, file):
    for relpath, dirs, files in os.walk(project_path):
        # print(files)
        for f in files:
            if file in f and relpath == 'da':
                return os.path.join(project_path, relpath, file)


def get_relative_path(r_path):
    if '\\' in r_path:
        flag = '\\'
    else:
        flag = '/'
    p_list = r_path.split(flag)
    if len(p_list) >= 2:
        p = p_list[-2:]
        return p[0], p[1]
    else:
        return None


@func_timer
def update_detection_result(project_path, start_time='2000-01-01 00:00:00'):
    db = connect()
    cur = db.cursor()
    sql_1 = """SELECT ft.build_id,ft.FAILED_TEST_NAME,ft.statement_cover,ft.file_cover,ft.flaky_frequency,
               bh.previous_state,bh.commit_sha,bh.created_time, ft.path
               FROM failed_tests ft JOIN build_history bh
               ON ft.build_id = bh.build_id
               having bh.created_time>'%s'
               ORDER BY bh.created_time desc""" % start_time
    all_failed_tests = search(sql_1)
    sql = ''
    try:
        for test in all_failed_tests:
            if test[5] == 'passed':
                previous_state = 0
            elif test[5] == 'failed':
                previous_state = 1
            elif test[5] == 'None':
                previous_state = 2
            else:
                previous_state = 3
            sql_pre = """update failed_tests set previous_state='%d'
                         where failed_test_name='%s' and build_id='%s'""" % (previous_state, test[1], test[0])
            cur.execute(sql_pre)  # update previous state

            relative_path, file = get_relative_path(test[8])
            checkout_commit(test[6], project_path)
            abs_path = get_abspath(project_path, relative_path, file)
            smells = 0
            size = 0
            if relative_path and file and abs_path:
                size = get_test_size(abs_path, test[1])
                smell = get_test_smell_method(abs_path, test[1])
                if size > 0:
                    if smell:
                        for s in smell:
                            smells += s[2]
                    else:
                        smells = 0
                    sql_size_smells = """update failed_tests set `size`='%d', smells='%d'
                                                                where failed_test_name='%s' and build_id='%s'""" % (
                        size, smells, test[1], test[0])
                    cur.execute(sql_size_smells)  # update size and smells
            if test[5] == 'passed':
                if test[2] == 'F':
                    sql = """update failed_tests set detection_result='F', detection_method='T'
                             where failed_test_name='%s' and build_id='%s'""" % (test[1], test[0])
                else:
                    sql = """update failed_tests set detection_result='N', detection_method='T'
                             where failed_test_name='%s' and build_id='%s'""" % (test[1], test[0])
            else:
                if relative_path and file and abs_path:
                    if size > 0:
                        flaky_frequency = test[4]

                        if test[2] == 'F':
                            dependency_cover = 0
                        else:
                            dependency_cover = 1
                        factors = [flaky_frequency, dependency_cover, smells, previous_state, size]
                        result, p = KNN_predict('dataset.csv', [factors])
                        if p[1] > 0.7:
                            res = 'F'
                        else:
                            res = 'N'
                        sql = """update failed_tests set detection_result='%s', detection_method='M'
                                 where failed_test_name='%s' and build_id='%s'""" % (res, test[1], test[0])
                        sql_size_smells = """update failed_tests set `size`='%d', smells='%d'
                                             where failed_test_name='%s' and build_id='%s'""" % (
                            size, smells, test[1], test[0])
                        cur.execute(sql_size_smells)  # update size and smells
                    else:
                        sql = """update failed_tests set detection_result='M', detection_method='M'
                                                     where failed_test_name='%s' and build_id='%s'""" % (
                            test[1], test[0])
                else:
                    sql = """update failed_tests set detection_result='M', detection_method='M'
                             where failed_test_name='%s' and build_id='%s'""" % (test[1], test[0])
            cur.execute(sql)  # update detection results
    except Exception as e:
        db.rollback()
        print("error: " + str(e))
        print(traceback.format_exc())
        print("rollback!")

    finally:
        db.commit()
        cur.close()
        db.close()


def update_multi_results():
    db = connect()
    cur = db.cursor()
    sql = """select build_id, failed_test_name, flaky_frequency, statement_cover, smells, previous_state, `size`
             from failed_tests where detection_method='M' and detection_result!='M'"""
    results = search(sql)
    try:
        for test in results:
            if test[3] == 'F':
                dependency_cover = 0
            else:
                dependency_cover = 1

            factors = [test[2], dependency_cover, test[4], test[5], test[6]]
            result, p = KNN_predict('dataset.csv', [factors])
            if p[1] > 0.7:
                res = 'F'
            else:
                res = 'N'
            update = """update failed_tests set detection_result='%s', detection_method='M'
                        where failed_test_name='%s' and build_id='%s'""" % (res, test[1], test[0])
            cur.execute(update)
    except Exception as e:
        db.rollback()
        print("error: " + str(e))
        print(traceback.format_exc())
        print("rollback!")

    finally:
        db.commit()
        cur.close()
        db.close()


if __name__ == '__main__':
    path = r'D:\CoursesResources\MasterThesis\Python_projects\spaCy\spacy'
    # time1 = time.time()
    # smell_project = get_test_smell_project(path)
    # for key, value in smell_project.items():
    #     print(key, value)
    # time2 = time.time()
    # print('cost time: ' + str(time2 - time1))
    # print(connect())
    # save_case_and_smells(path)

    project_owner = "apache"
    project_name = "incubator-superset"
    update_detection_result(path)
    # update_flaky_frequency()
    # passed_builds = get_all_builds(project_owner, project_name, "passed", 10)
    # save_passed_builds(passed_builds)
    # failed_test_list = get_all_builds(project_owner, project_name, 8)
    # failed_test_dic = get_failed_tests(failed_test_list)
    # save_failed_builds_and_tests(failed_test_list, failed_test_dic, path)
    # create_tables()
