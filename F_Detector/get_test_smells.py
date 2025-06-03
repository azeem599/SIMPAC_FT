import ast
from multiprocessing.pool import Pool
from path_process import get_test_files
from dependency_analysis import get_classless_functions, get_all_class_methods, get_call
import time


class TestSmell:
    """Checks for violations of a particular test smell

    Subclass this to create classes responsible for detecting test smells.
    These subclasses handle one smell each, and are given either a list of
    python files, a test case ast, or a test method ast to check
    """
    flakiness_type = None
    flakiness_name = None
    visitor = None
    additional_process = None

    def test_for_smell(self, node):
        self.visitor.visit(node)
        self.visitor.additional_process(node)
        count = self.visitor.results['count']
        lines = self.visitor.results['lines']
        if count > 0:
            output = [self.flakiness_type, self.flakiness_name, count, lines]
        else:
            output = None
        return output


class SmellVisitor(ast.NodeVisitor):

    def __init__(self):
        self.results = dict()
        self.results["count"] = 0
        self.results["lines"] = list()

    def additional_process(self, node):
        pass


class AssertVisitor(ast.NodeVisitor):

    def __init__(self):
        self.assert_list = list()

    def visit_Assert(self, node):
        self.assert_list.append(node)

    def generic_visit(self, node):
        pass


class CallVisitor(ast.NodeVisitor):

    def __init__(self):
        self.call_list = list()

    def visit_Call(self, node):
        self.call_list.append(node)

    def generic_visit(self, node):
        pass


def get_call_name(call_node):
    if not isinstance(call_node, ast.Call):
        # print("this node is " + str(type(call_node)) + " node, not call node")
        return None
    elif isinstance(call_node.func, ast.Call):
        pass
    elif isinstance(call_node.func, ast.Name):
        return call_node.func.id
    elif isinstance(call_node.func, ast.Attribute):
        if isinstance(call_node.func.value, ast.Name):
            return call_node.func.attr
        else:
            get_call_name(call_node.func.value)


class Sleep(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Async Wait'
        self.flakiness_name = 'sleep'
        self.visitor = SleepVisitor()


class SleepVisitor(SmellVisitor):
    """discovers whether a test method calls sleep-related functions"""

    def visit_Call(self, node):
        call = get_call_name(node)
        if call and 'sleep' in call:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)
        super().generic_visit(node)


class Waiting(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Async Wait'
        self.flakiness_name = 'wait'
        self.visitor = WaitingVisitor()


class WaitingVisitor(SmellVisitor):
    """discovers whether a test method calls wait-related functions"""

    def visit_Call(self, node):
        call = get_call_name(node)
        if call and 'wait' in call:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)
        super().generic_visit(node)


class Timeout(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Async Wait'
        self.flakiness_name = 'timeout'
        self.visitor = TimeoutVisitor()


class TimeoutVisitor(SmellVisitor):
    """discovers whether a test method calls timeout-related functions or has a timeout parameter"""

    def visit_Call(self, node):
        call = get_call_name(node)
        args = node.args
        keywords = node.keywords
        if call and 'timeout' in call:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)

        if args:
            for arg in args:
                if isinstance(arg, ast.Name) and 'timeout' in arg.id:
                    self.results['count'] += 1
                    self.results['lines'].append(node.lineno)
        if keywords:
            for keyword in keywords:
                if isinstance(keyword.arg, str) and 'timeout' in keyword.arg:
                    self.results['count'] += 1
                    self.results['lines'].append(node.lineno)

        super().generic_visit(node)


class AssertCompare(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Precision'
        self.flakiness_name = 'Assert Comparision'
        self.visitor = AssertCompareVisitor


class AssertCompareVisitor(SmellVisitor):
    """discovers whether a test method uses assert to compare two value"""

    def visit_Assert(self, node):
        if isinstance(node.test, ast.Compare):
            for op in node.test.ops:
                if isinstance(op, ast.Gt) or isinstance(op, ast.Lt):
                    self.results['count'] += 1
                    self.results['lines'].append(node.lineno)
        super().generic_visit(node)


class Tolerance(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Precision'
        self.flakiness_name = 'tolerance'
        self.visitor = ToleranceVisitor()


class ToleranceVisitor(SmellVisitor):
    """discovers whether a test method uses check_numeric_gradient, check_consistency, assert_almost_equal
    or assert_allclose
    """

    def visit_Call(self, node):
        call = get_call(node)
        call_with_tol = ['check_numeric_gradient', 'check_consistency', 'assert_almost_equal', 'assert_allclose']
        if call and call in call_with_tol:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)
        super().generic_visit(node)


class Float(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Precision'
        self.flakiness_name = 'float'
        self.visitor = FloatVisitor()


class FloatVisitor(SmellVisitor):
    """discovers whether a test method uses float"""

    def visit_Call(self, node):
        call = get_call(node)
        if call and 'float' in call:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)
        super().generic_visit(node)


# class AssertUnorderedCollection(TestSmell):
# #
# #     def __init__(self):
# #         self.flakiness_type = 'Unordered Collection'
# #         self.flakiness_name = 'assert unordered collection equal'
# #         self.visitor =
# #
# #
# # class AssertUnorderedCollectionVisitor(SmellVisitor):
# #     """discovers whether a test method compare two unordered collections"""
# #
# #     def visit_Assert(self, node):
# #         pass
# #
# #     def visit_Call(self, node):
# #         call = get_call(node)
# #         if call and 'assertEqual' in call:
# #             pass


class WithSeed(TestSmell):
    def __init__(self):
        self.flakiness_type = 'Randomness'
        self.flakiness_name = '@with_seed'
        self.visitor = WithSeedVisitor()


class WithSeedVisitor(SmellVisitor):
    """discovers whether a test method has a decorator @with_seed"""

    def visit_FunctionDef(self, node):
        decorator = node.decorator_list
        if decorator:
            for dec in decorator:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                    if 'with_seed' in dec.func.id and dec.args:
                        self.results['count'] += 1
                        self.results['lines'].append(node.lineno)
        super().generic_visit(node)


class RandomWithoutSeed(TestSmell):
    def __init__(self):
        self.flakiness_type = 'Randomness'
        self.flakiness_name = 'random without seed'
        self.visitor = RandomWithoutSeedVisitor()


class RandomWithoutSeedVisitor(SmellVisitor):
    """discovers whether a test method uses random without seed"""

    def __init__(self):
        super().__init__()
        self.with_seed = False

    def visit_Call(self, node):
        call = get_call(node)
        if call and 'seed' in call:
            self.with_seed = True

        if call and 'random' in call:
            if node.keywords:
                for keyword in node.keywords:
                    if isinstance(keyword, str) and 'seed' in keyword.arg:
                        self.with_seed = True
            if not self.with_seed:
                self.results['count'] += 1
                self.results['lines'].append(node.lineno)

        super().generic_visit(node)


class Url(TestSmell):
    def __init__(self):
        self.flakiness_type = 'Network'
        self.flakiness_name = 'URL'
        self.visitor = UrlVisitor()


class UrlVisitor(SmellVisitor):
    """discovers whether a test method uses url"""

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'url':
                self.results['count'] += 1
                self.results['lines'].append(node.lineno)

        super().generic_visit(node)

    def visit_Call(self, node):

        for n in ast.walk(node):
            if isinstance(n, ast.keyword) and n.arg and n.arg == 'url':
                self.results['count'] += 1
                self.results['lines'].append(node.lineno)

            elif isinstance(n, ast.Name) and n.id == 'url':
                self.results['count'] += 1
                self.results['lines'].append(node.lineno)

            elif isinstance(n, ast.Str) and \
                    ('http' in n.s or 'https' in n.s or 'www.' in n.s or '.org' in n.s or '.com' in n.s):
                self.results['count'] += 1
                self.results['lines'].append(node.lineno)

        super().generic_visit(node)


class Socket(TestSmell):
    def __init__(self):
        self.flakiness_type = 'Network'
        self.flakiness_name = 'socket'
        self.visitor = SocketVisitor()


class SocketVisitor(SmellVisitor):
    """discovers whether a test method uses socket.connect, socket.settimeout or socket.gethostbyname"""

    def visit_Call(self, node):
        call = get_call(node)
        if call in ['socket.connect', 'socket.settimeout', 'socket.gethostbyname']:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)

        super().generic_visit(node)


class AssertCalledWith(TestSmell):
    def __init__(self):
        self.flakiness_type = 'Network'
        self.flakiness_name = 'assert_called_with'
        self.visitor = AssertCalledWithVisitor()


class AssertCalledWithVisitor(SmellVisitor):
    """discovers whether a test method uses assert_called_with"""

    def visit_Call(self, node):
        call = get_call(node)
        if call and 'assert_called_with' in call:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)

        super().generic_visit(node)


class NotCheckExistence(TestSmell):

    def __init__(self):
        self.flakiness_type = 'IO'
        self.flakiness_name = 'Resource Operation without Checking Existence'
        self.visitor = NotCheckExistenceVisitor()


class NotCheckExistenceVisitor(SmellVisitor):
    """discovers whether a test method operates a resource without checking existence"""

    def __init__(self):
        super().__init__()
        self.open_found = False
        self.open_with_try = False
        self.with_open = False
        self.with_support_temp_cwd = False
        self.with_os_mkdir = False
        self.not_with_os_mkdir = False
        self.os_dir_with_try = False
        self.os_dir_without_try = False
        self.os_path_exists = False
        self.os_dir_list = ['os.chdir', 'os.chroot', 'os.makedirs', 'os.listdir', 'os.mkdir',
                            'os.mkfifo', 'os.open', 'os.pathconf', 'os.remove', 'os.removedirs',
                            'os.rmdir', 'os.unlink']
        self.open_line = 0
        self.os_dir_line = 0

    def visit_Try(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                call = get_call(n)
                if call and 'open' in call:
                    self.open_with_try = True

                if call and call in self.os_dir_list:
                    self.os_dir_with_try = True

        super().generic_visit(node)

    def visit_With(self, node):
        call = get_call(node)
        if call and 'temp_cwd' in call:
            self.with_support_temp_cwd = True

        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                call = get_call(n)
                if call and 'mkdir' in call:
                    self.with_os_mkdir = True
            elif isinstance(n, ast.withitem):
                for m in ast.walk(n):
                    if isinstance(m, ast.Call):
                        call_m = get_call(m)
                        if call_m and 'open' in call_m:
                            self.with_open = True

        super().generic_visit(node)

    def visit_Call(self, node):
        call = get_call(node)
        if call:
            if 'open' in call:
                self.open_found = True
                self.open_line = node.lineno

            if call == 'mkdir':
                self.not_with_os_mkdir = True
                self.os_dir_line = node.lineno

            if call in self.os_dir_list:
                self.os_dir_without_try = True
                self.os_dir_line = node.lineno

            if 'exists' in call:
                self.os_path_exists = True

        super().generic_visit(node)

    def additional_process(self, node):

        if self.open_found and not self.open_with_try and not self.with_open:
            self.results['count'] += 1
            self.results['lines'].append(self.open_line)

        if self.not_with_os_mkdir and not self.with_os_mkdir and \
                not self.with_support_temp_cwd and not self.os_path_exists:
            self.results['count'] += 1
            self.results['lines'].append(self.os_dir_line)

        if self.os_dir_without_try and not self.os_dir_with_try and not self.os_path_exists:
            self.results['count'] += 1
            self.results['lines'].append(self.os_dir_line)


class OpenWithoutClose(TestSmell):

    def __init__(self):
        self.flakiness_type = 'IO'
        self.flakiness_name = 'Open a file without close it'
        self.visitor = OpenWithoutCloseVisitor()


class OpenWithoutCloseVisitor(SmellVisitor):
    """discovers whether a test method open a file without close it"""

    def __init__(self):
        super().__init__()
        self.open = False
        self.close = False
        self.with_open = False
        self.open_line = 0

    def visit_With(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.withitem):
                for m in ast.walk(n):
                    if isinstance(m, ast.Call):
                        call = get_call(m)
                        if call and 'open' in call:
                            self.with_open = True

        super().generic_visit(node)

    def visit_Call(self, node):
        call = get_call(node)
        if call and 'open' in call:
            self.open = True
            self.open_line = node.lineno

        if call and 'close' in call:
            self.close = True

        super().generic_visit(node)

    def additional_process(self, node):

        if self.open and not self.close and not self.with_open:
            self.results['count'] += 1
            self.results['lines'].append(self.open_line)


class ForInRange(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Training'
        self.flakiness_name = 'For in range'
        self.visitor = ForInRangeVisitor()


class ForInRangeVisitor(SmellVisitor):
    """discovers whether a test method uses for _ in range"""

    def visit_For(self, node):
        if isinstance(node.iter, ast.Call):
            call = get_call(node.iter)
            if call and isinstance(node.target, ast.Name):
                if 'range' in call:
                    self.results['count'] += 1
                    self.results['lines'].append(node.lineno)

        super().generic_visit(node)


class DatetimeNow(TestSmell):

    def __init__(self):
        self.flakiness_type = 'Time'
        self.flakiness_name = 'datetime.now'
        self.visitor = DatetimeNowVisitor()


class DatetimeNowVisitor(SmellVisitor):
    """discovers whether a test method uses datetime.now"""

    def visit_Call(self, node):
        call = get_call(node)
        if call and 'datetime.now' in call:
            self.results['count'] += 1
            self.results['lines'].append(node.lineno)

        super().generic_visit(node)


def test_smell_runner(method_node):
    smell_list = list()
    smell_list.append(Sleep())
    smell_list.append(Waiting())
    smell_list.append(Timeout())
    smell_list.append(WithSeed())
    smell_list.append(RandomWithoutSeed())
    smell_list.append(Url())
    smell_list.append(Socket())
    smell_list.append(AssertCalledWith())
    smell_list.append(NotCheckExistence())
    smell_list.append(OpenWithoutClose())
    smell_list.append(ForInRange())
    smell_list.append(DatetimeNow())

    output = list()

    for smell in smell_list:
        result = smell.test_for_smell(method_node)
        if result:
            output.append(result)
    return output


def get_spaces_number_front_def(code_line):
    space_number = 0
    if code_line.split(' ')[0] != '':
        space_number = 0
    else:
        for x in code_line.split(' '):
            if x == '':
                space_number += 1
            elif x == 'def' or x == 'async' or x == 'await':
                break
    return space_number


def get_size(test_method, lines):
    line_num = 0
    found = False
    test_space = 0
    for line in lines:
        if line.strip().startswith('def' + ' ' + test_method + '('):
            test_space = get_spaces_number_front_def(line)
            found = True
        elif found and line.strip() != '':
            if line.strip().startswith('def') or line.strip().startswith('class') or line.strip().startswith(
                    'async def') \
                    or line.strip().startswith('await def') or line.strip().startswith('@'):
                temp_space = get_spaces_number_front_def(line)
                if temp_space <= test_space:
                    found = False
                    break
                else:
                    line_num += 1
            else:
                line_num += 1

    return line_num


def get_test_size(file_abspath, test_method):
    try:
        f = open(file_abspath, encoding='gb18030', errors='ignore')
        # print("open done")
    except IOError:
        print('test file not found or file read failed')
        return False
    else:
        lines = f.readlines()
        line_num = get_size(test_method, lines)
        f.close()
        return line_num


def get_size_file(file_abspath):
    with open(file_abspath, encoding='gb18030', errors='ignore', mode='r') as f:
        lines = f.readlines()
        # f = open(file_abspath, encoding='gb18030', errors='ignore', mode='r')
        # print("open done")
    with open(file_abspath, encoding='gb18030', errors='ignore', mode='r') as f1:
        file_node = ast.parse(f1.read())
    test_methods = get_test_methods(file_node)
    size_dic = dict()
    for method in test_methods:
        size_dic[method[1].name] = get_size(method[1].name, lines)
    return size_dic


def get_test_smell_method(file_abspath, test_method):
    try:
        with open(file_abspath, encoding='gb18030', errors='ignore') as f:
            root_node = ast.parse(f.read())

        methods = get_test_methods(root_node)
        for method in methods:
            if method[1].name == test_method:
                return test_smell_runner(method[1])
        return None

    except FileNotFoundError:
        print('file not found:', file_abspath)


def get_test_smell_file(file_abspath):
    with open(file_abspath, encoding='gb18030', errors='ignore') as f:
        file_node = ast.parse(f.read())
    smell_list = list()
    test_methods = get_test_methods(file_node)

    for test_method in test_methods:
        smell = test_smell_runner(test_method[1])
        smell_dic = {}
        if smell:
            class_and_method = test_method[1].name
            # if not test_method[0] == 'None':
            #     class_and_method = test_method[0] + '::' + test_method[1].name
            # else:
            #     class_and_method = test_method[1].name

            # smell.append(test_method[0])    # add the class of the test method
            # smell.append(test_method[1].name)   # add the name of the test method
            # smell.append(file_abspath)      # add the absolute path of the file
            if class_and_method not in smell_dic:
                smell_dic[class_and_method] = list()
                smell_dic[class_and_method].extend(smell)
            else:
                smell_dic[class_and_method].extend(smell)
            smell_list.append(smell_dic)

    return smell_list


def get_test_smell_project(project_path):
    test_files_list = get_test_files(project_path)
    smell_dic = dict()
    pool = Pool(5)
    for file in test_files_list:
        smell = pool.apply_async(get_test_smell_file, args=(file,)).get()
        smell_dic[file] = smell
    pool.close()
    pool.join()
    return smell_dic


def get_test_methods(file_node):
    test_methods = list()
    classless_methods = get_classless_functions(file_node)
    class_methods = get_all_class_methods(file_node)
    for classless_method in classless_methods:
        if classless_method[1].name.startswith('test_') or classless_method[1].name.endswith('_test') or \
                classless_method[1].name.endswith('_tests'):
            test_methods.append(classless_method)

    for class_method in class_methods:
        if class_method[1].name.startswith('test_') or class_method[1].name.endswith('_test') or \
                class_method[1].name.endswith('_tests'):
            test_methods.append(class_method)

    return test_methods


if __name__ == '__main__':
    path = r'D:\CoursesResources\MasterThesis\flakytestdetectormszhixiang\test_code'
    # test_file = get_test_files(path)
    # for file in test_file:
    #     print(file)
    file_path = r'D:\CoursesResources\MasterThesis\Python_projects\incubator-superset\tests\sqllab_tests.py'
    # test_files = get_test_files(path)
    res = get_test_smell_file(file_path)
    for r in res:
        print(r)
    time1 = time.time()
    # for file in test_files:
    #     with open(file, encoding='gb18030', errors='ignore') as f:
    #         node = ast.parse(f.read())
    #     methods = get_test_methods(node)
    #     for method in methods:
    #         print(file, method[0], method[1].name)
    # time2 = time.time()
    # smell_project = get_test_smell_project(path)
    # for key, value in smell_project.items():
    #     print(key, value)
    # time2 = time.time()
    # print('time: ' + str(time2 - time1))
