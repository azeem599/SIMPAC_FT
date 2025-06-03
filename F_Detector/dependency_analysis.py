import ast
import time
import re
import os
from path_process import get_abspath


class ClasslessFunctionVisitor(ast.NodeVisitor):
    """Visit each function that does not exist inside a class
    Given a module, store the name of each fuction that does not reside within a class
    """

    def __init__(self):
        self.function_list = list()

    def visit_ClassDef(self, node):
        pass

    def visit_FunctionDef(self, node):
        add = ['None', node]
        self.function_list.append(add)

    def visit_AsyncFunctionDef(self, node):
        add = ['None', node]
        self.function_list.append(add)


def get_classless_functions(root_node):
    """List functions in a given module

    Take a module ast and return a list of function asts that reside in the
    given module ast
    """

    file_ast = ast.parse(root_node)

    visitor = ClasslessFunctionVisitor()

    visitor.visit(file_ast)

    return visitor.function_list


def get_all_class_methods(root_node):
    classes_list = []
    for node in ast.walk(root_node):
        if isinstance(node, ast.ClassDef):
            methods_list = get_class_methods(node)
            for method in methods_list:
                class_list = [node.name, method]
                classes_list.append(class_list)
    return classes_list


def get_class_methods(class_ast):
    """List methods in a given class

    Take a class ast and return a list of method asts that reside in the given
    module ast
    """
    output = list()

    # only checks definitions immediately in body to avoid nested class methods
    for node in class_ast.body:
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            output.append(node)

    return output


class ImportVisitor(ast.NodeVisitor):
    """Visits AST nodes to find imports in each file.
    Return import names in each file.
    """

    def visit_Import(self, node):
        imports_list = list()
        for alias in node.names:
            import_list = list()
            import_list.append(alias.name)
            import_list.append(alias.asname)
            imports_list.append(import_list)
        return imports_list  # [[module1, alias1], [module2, alias2], ...]


class ImportFromVisitor(ast.NodeVisitor):

    def visit_ImportFrom(self, node):
        imports_dic = dict()
        imports_list = list()
        for alias in node.names:
            import_list = list()
            import_list.append(alias.name)
            import_list.append(alias.asname)
            imports_list.append(import_list)
        imports_dic[node.module] = imports_list
        return imports_dic  # {module: [[method1/class1, alias1], [method2/class2, alias2], ...]}


def get_imports(root_node):
    """
    List import infomation in a module/file.
    :param root_node:
    :return:
    """
    imports = {'NotImportFrom': []}
    for node in ast.walk(root_node):
        if isinstance(node, ast.Import):
            import_visitor = ImportVisitor()
            t = import_visitor.visit_Import(node)
            imports['NotImportFrom'].extend(t)

        elif isinstance(node, ast.ImportFrom):
            import_from_visitor = ImportFromVisitor()
            r = import_from_visitor.visit_ImportFrom(node)
            imports.update(r)
    return imports


class GetCalls(ast.NodeVisitor):
    """
    get calls, return a list, like ['numpy', 'random']
    """

    def __init__(self):
        self.calls = list()

    def visit_Call(self, node):

        child_node = node.func

        if isinstance(child_node, ast.Name):
            self.calls.append(child_node.id)

        elif isinstance(child_node, ast.Attribute):
            if isinstance(child_node.value, ast.Name):
                self.calls.append(child_node.value.id)
                self.calls.append(child_node.attr)
            elif isinstance(child_node.value, ast.Call):
                self.visit_Call(child_node.value)
                # self.calls.append(child_node.attr)

            else:
                for n in ast.walk(child_node):
                    if isinstance(n, ast.Call):
                        self.visit_Call(n)

        elif isinstance(child_node, ast.Call):
            self.visit_Call(child_node)

        else:
            for n in ast.walk(child_node):
                if isinstance(n, ast.Call):
                    self.visit_Call(n)


def get_call(call_node):
    """
    get calls,  return a string, like numpy.random
    :param call_node:
    :return:
    """
    if not isinstance(call_node, ast.Call):
        # print("this node is " + str(type(call_node)) + " node, not call node")
        return None

    elif isinstance(call_node.func, ast.Name):
        return call_node.func.id

    elif isinstance(call_node.func, ast.Attribute):
        if isinstance(call_node.func.value, ast.Name):
            return call_node.func.value.id + '.' + call_node.func.attr
        else:
            get_call(call_node.func.value)

    elif isinstance(call_node.func, ast.Call):
        get_call(call_node.func)


def get_function_call(function_node):
    call_list = []
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            # call = get_call(node)
            call = GetCalls()
            call.visit(node)
            if call.calls and call.calls not in call_list:
                call_list.append(call.calls)
    return call_list


def get_dependency(file_path, test_method):
    with open(file_path) as f:
        root_node = ast.parse(f.read())
    for node in ast.walk(root_node):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if node.name == test_method:
                call_list = get_function_call(node)
                return call_list, node.lineno


class MethodDependencyVisitor(ast.NodeVisitor):

    def __init__(self, project_path, module_path, method_class, method):

        self.project_path = project_path
        self.module_path = module_path
        self.method_class = method_class
        self.method = method

        self.method_found = False
        self.module_dir = os.path.split(module_path)[0]
        self.class_methods = []
        self.classless_methods = []
        self.method_calls = []
        self.clean_calls = []
        self.imports = {}
        self.call_alias = {}  # the alias of a class or method, for instance: df = DataFrame,
        # df is the alias of class DataFrame
        self.project_py_modules = []
        self.potential_calls_list = []
        self.dependencies = []  # [(abspath_1, method_class_1, method_1), (abspath_2, method_class_2, method_2, ...]

        try:
            with open(self.module_path, encoding='gb18030', errors='ignore') as f:
                node = ast.parse(f.read())
            self.ast_node = node
        except FileNotFoundError as e:
            print(repr(e))
            exit(1)
        except PermissionError as p:
            print(repr(p))
            exit(1)

        self.process()

    def process(self):
        # self.visit(self.ast_node)
        self.classless_methods = get_classless_functions(self.ast_node)
        self.get_class_methods_with_base(self.ast_node)
        self.get_method_calls(self.class_methods, self.classless_methods)
        if not self.method_found:
            exit(1)
        self.imports = get_imports(self.ast_node)
        self.get_call_alias(self.ast_node)
        self.update_calls(self.method_calls, self.call_alias, self.imports)
        self.clean_method_calls()
        self.project_py_modules = get_py_modules(self.project_path)
        # self.potential_calls(self.imports, self.class_methods, self.classless_methods)

    def get_method_calls(self, class_methods, classless_methods):

        def get_calls(node):
            self.method_found = True

            for nd in ast.walk(node):
                if isinstance(nd, ast.Call):
                    calls = GetCalls()
                    calls.visit(nd)
                    if calls.calls and calls.calls not in self.method_calls:
                        self.method_calls.append(calls.calls)

        if self.method_class == 'None':
            for method in classless_methods:
                if method[1].name == self.method:
                    get_calls(method[1])

        else:
            for method in class_methods:
                if method[1] == self.method_class and method[2].name == self.method:
                    get_calls(method[2])

        if not self.method_found:
            print('method not exist!!!')

    def get_class_methods_with_base(self, node):

        for n in ast.walk(node):
            if isinstance(n, ast.ClassDef):

                base = []
                for b in n.bases:
                    if isinstance(b, ast.Attribute):
                        base.append(b.value.id + '.' + b.attr)
                    elif isinstance(b, ast.Name):
                        base.append(b.id)

                method_nodes = get_class_methods(n)
                for method in method_nodes:
                    class_list = [base, n.name, method]
                    self.class_methods.append(class_list)

    def get_call_alias(self, node):

        def visit_assign(assign):
            if isinstance(assign, ast.Assign):
                if isinstance(assign.value, ast.Call):
                    c = GetCalls()
                    c.visit_Call(assign.value)
                    for alias in assign.targets:
                        if c.calls and isinstance(alias, ast.Name):
                            self.call_alias[alias.id] = c.calls

        def get_method_call_alias(method_node):  # get call alias within a method
            if (isinstance(method_node, ast.FunctionDef) or isinstance(method_node, ast.AsyncFunctionDef)) \
                    and method_node.name == self.method:

                for a in ast.walk(method_node):
                    visit_assign(a)

        for n in ast.iter_child_nodes(node):
            # global call aliases
            visit_assign(n)

            if self.method_class == 'None':  # classless method call aliases
                get_method_call_alias(n)

            else:

                if isinstance(n, ast.ClassDef) and n.name == self.method_class:

                    for assign in ast.iter_child_nodes(n):
                        if isinstance(assign, ast.Assign):  # class call aliases
                            if isinstance(assign.value, ast.Call):
                                for alias in assign.targets:
                                    self.call_alias[alias] = GetCalls().visit(n.value).calls

                        get_method_call_alias(assign)

    @staticmethod
    def update_calls(method_calls, call_alias, imports):
        # replace the alias name of call with the original call name
        for ca in method_calls:
            for k, v in call_alias.items():
                if ca[0] == k:
                    v.reverse()
                    ca.pop(0)
                    for c in v:
                        ca.insert(0, c)

            for k, v in imports.items():
                for n in v:
                    if ca[0] == n[1]:
                        ca[0] = n[0]

    # get potential calls, include other methods in the module and methods from other module of the project
    # exclude the calls from python standard lib and other projects
    def potential_calls(self, imports_dic, class_methods, classless_methods):

        # get potential calls from imports
        for k, v in imports_dic.items():
            if k == 'NotImportFrom':
                for module in v:
                    m_path = import_abspath(module[0], self.project_path)
                    if m_path:
                        self.potential_calls_list.append([m_path, 'None', '*'])  # * means all the methods of the module
            else:
                for module in v:
                    m_path = import_abspath(k, self.project_path)
                    if m_path:
                        if re.match(r'[A-Z].+?', module[0]):
                            self.potential_calls_list.append([m_path, module[0], '*'])
                        else:
                            self.potential_calls_list.append([m_path, 'None', module[0]])
                    else:
                        alter = k + '.' + module[0]
                        alter_m_path = import_abspath(alter, self.project_path)
                        if alter_m_path:
                            self.potential_calls_list.append([alter_m_path, 'None', '*'])

        # get potential calls from the module self
        for class_method in class_methods:
            self.potential_calls_list.append([self.module_path, class_method[1], class_method[2].name])

        for classless_method in classless_methods:
            self.potential_calls_list.append([self.module_path, 'None', classless_method[1].name])

    def clean_method_calls(self):

        for call in self.method_calls:
            if call[0] == 'self':
                self.clean_calls.append(call)
            elif re.match(r'[[A-Z].+?]', call[0]):
                self.clean_calls.append(call)
            else:
                for method in self.classless_methods:
                    if call[0] == method[1]:
                        self.clean_calls.append(call)

                for k, v in self.imports.items():

                    if k == 'NotImportFrom':
                        for n in v:
                            if n[0] == call[0]:
                                self.clean_calls.append(call)
                    else:
                        for n in v:
                            if n[0] == call[0]:
                                self.clean_calls.append(call)

    def get_dependencies(self):

        for call in self.clean_calls:
            for k, v in self.imports.items():  # get dependencies from imports
                if k == 'NotImportFrom':
                    for module in v:
                        if module[0] == call[0]:
                            m_path = import_abspath(module[0], self.project_path)
                            if m_path:
                                self.dependencies.append([m_path, 'None', '*'])  # * means all the methods of the module

                else:
                    for module in v:
                        if module[0] == call[0]:
                            m_path = import_abspath(k, self.project_path)
                            if m_path:
                                if re.match(r'[A-Z].+?', module[0]):
                                    if call[1]:
                                        self.dependencies.append([m_path, module[0], call[1].name])
                                    else:
                                        self.dependencies.append([m_path, module[0], '__init__'])
                                else:
                                    self.dependencies.append([m_path, 'None', module[0]])
                            else:
                                alter = k + '.' + module[0]
                                alter_m_path = import_abspath(alter, self.project_path)
                                if alter_m_path:
                                    self.dependencies.append([alter_m_path, 'None', '*'])

            for method in self.classless_methods:

                if method[1] == call[0]:
                    self.dependencies.append([self.module_path, 'None', method[1].name])

            for method in self.class_methods:

                if call[0] == 'self':
                    if method[0] is None:
                        if method[2].name == call[1].name:
                            self.dependencies.append([self.module_path, method[1], call[1].name])

                    else:
                        if method[2].name == call[1].name:
                            self.dependencies.append([self.module_path, method[1], call[1].name])
                        else:
                            for baseclass in method[0]:
                                if '.' in baseclass:
                                    base = baseclass.split('.')
                                    for k, v in self.imports.items():
                                        for n in v:
                                            if n[0] == base[0]:
                                                if k == 'NotImportFrom':
                                                    m_path = import_abspath(n[0], self.project_path)
                                                    if m_path:
                                                        self.dependencies.append([m_path, base[1], call[1].name])
                                                else:
                                                    m_path = import_abspath(k, self.project_path)
                                                    if m_path:

                                                        self.dependencies.append([m_path, base[1], call[1].name])

                                                    else:
                                                        alter = k + '.' + n[0]
                                                        alter_m_path = import_abspath(alter, self.project_path)
                                                        if alter_m_path:
                                                            self.dependencies.append(
                                                                [alter_m_path, base[1], call[1].name])
                                else:
                                    for k, v in self.imports.items():
                                        for n in v:
                                            if n[0] == baseclass:
                                                if k == 'NotImportFrom':
                                                    m_path = import_abspath(n[0], self.project_path)
                                                    if m_path:
                                                        self.dependencies.append([m_path, baseclass, call[1].name])
                                                else:
                                                    m_path = import_abspath(k, self.project_path)
                                                    if m_path:

                                                        self.dependencies.append([m_path, baseclass, call[1].name])

                                                    else:
                                                        alter = k + '.' + n[0]
                                                        alter_m_path = import_abspath(alter, self.project_path)
                                                        if alter_m_path:
                                                            self.dependencies.append(
                                                                [alter_m_path, baseclass, call[1].name])

                else:
                    pass


def import_abspath(import_, project_path):
    import_ = import_.lstrip('.')
    im_list = import_.split('.')
    im_module = im_list.pop()
    im_module = im_module + '.py'

    if im_list:
        relative_path = ''
        for im in im_list:
            relative_path = os.path.join(relative_path, im)
        im_abspath = get_abspath(project_path, relative_path, im_module)
        if im_abspath:
            return im_abspath
        else:
            return None

    else:
        im_abspath = get_abspath(project_path, '', im_module)
        if im_abspath:
            return im_abspath
        else:
            return None


def get_py_modules(project_path):
    # get all the python files in the project
    py_list = []
    for relpath, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_abspath = os.path.join(project_path, relpath, file)
                py_list.append(file_abspath)

    return py_list


if __name__ == '__main__':
    time1 = time.time()
    project = r'D:\CoursesResources\MasterThesis\flakytestdetectormszhixiang\flaky_extractor\public_project'
    relative = r'pandas\core'
    file = 'apply.py'
    test_method = 'test_deferred_with_groupby'
    # abspath = get_abspath(project, relative, file)
    abspath = r'D:\CoursesResources\MasterThesis\Python_projects\pandas\pandas\tests\resample\test_resampler_grouper.py'
    dependency = MethodDependencyVisitor(project, abspath, 'None', test_method)
    print('\nmethod calls: ')
    for call in dependency.method_calls:
        print(call)

    print('\nclass methods:')
    for m in dependency.class_methods:
        print(m[0], m[1], m[2].name)

    print('\nclassless methods: ')
    for m in dependency.classless_methods:
        print(m[0], m[1].name)

    print('\nimports: ')
    for key, value in dependency.imports.items():
        print(key, value)

    print('\ncall aliases: ')
    for key, value in dependency.call_alias.items():
        print(key, value)

    print('\npotential calls:')
    for call in dependency.potential_calls_list:
        print(call[0], call[1], call[2])

    print('\nclean calls:')
    for call in dependency.clean_calls:
        print(call)
    time2 = time.time()
    print('time:', str(time2 - time1))
    # print(re.split(r'[/]|[\\]', relative))
    # call_list, line = get_dependency(abspath, test_method)
    # imports = get_imports(abspath)
    # with open(abspath) as f:
    #     root_node = ast.parse(f.read())
    # print('imports: \n')
    # for key, value in imports.items():
    #     print(key, value)
    # print('\ncalls: \n')
    # print(call_list)
    # print('function_line: ' + str(line))
    # print('\nclassless functions: \n')
    # classless_functions = get_classless_functions(root_node)
    # for fun in classless_functions:
    #     print(fun[0], fun[1].name)
    # print('\nclass functions: \n')
    # class_functions = get_all_class_methods(root_node)
    # for fun in class_functions:
    #     print(fun[0], fun[1].name)
    # print(find)
