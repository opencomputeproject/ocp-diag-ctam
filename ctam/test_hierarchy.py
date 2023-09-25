"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""

import ast
import os
import importlib.util
import inspect
import sys
import os
import ast
from typing import List, Any


class TestHierarchy:
    """
    This scans the tests directory structure and creates hierarchal dictionary of test groups
    and their associated test cases

    """

    class ClassVisitor(ast.NodeVisitor):
        """
        ast is a module that does the heavy lifting of scanning python files and arranging file contents
        into an easily parsable structure. This helper class is derived from ast and allows for custom inspection.

        :param ast: _description_
        :type ast: _type_
        """

        def __init__(self):
            """
            Re-init class values after every class visit.  Code below saves this info first
            """
            self.test_groups = (
                {}
            )  # dictionary with key is TestGroup, and value is a List of Testcases
            self.test_cases = []  # list to store test_cases
            self.class_names = []
            self.current_group = None  # to store the current test group

        def eval_node(self, node: ast.AST) -> Any:
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.List):
                return [self.eval_node(elt) for elt in node.elts]
            elif isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Str):  # for python versions < 3.8
                return node.s
            else:
                raise ValueError(f"Unsupported node: {ast.dump(node)}")

        def visit_ClassDef(self, node):
            """
            As part of ast, this function is a callback called during the line below:
            visitor.visit(tree)

            The design requires a single Testgroup file in a directory with a variable number of test cases.
            It walks a directory and creates the test case list. Then it assigns to the test group in that class.
            This is so test case files can be processed before the test group file.
            The dictionary entry is added to TestHierarchy and then the values are cleared for the next
            directory that is found during the wak.

            :param node: ast node
            :type node: ast node
            """
            self.class_names.append(node.name)
            for base in node.bases:
                if isinstance(base, ast.Name):
                    if base.id == "TestGroup":
                        group_attributes = {
                            n.target.id: self.eval_node(n.value)
                            for n in node.body
                            if isinstance(n, (ast.Assign, ast.AnnAssign))
                            and isinstance(n.target, ast.Name)
                        }
                        self.test_groups[node.name] = {
                            "group_name": node.name,
                            "module_name": None,
                            "module_path": None,
                            "group_attributes": group_attributes,
                            "test_cases": [],
                        }
                        self.current_group = self.test_groups[
                            node.name
                        ]  # set current test group
                    elif base.id == "TestCase":
                        testcase_attributes = {
                            n.target.id: self.eval_node(n.value)
                            for n in node.body
                            if isinstance(n, (ast.Assign, ast.AnnAssign))
                            and isinstance(n.target, ast.Name)
                        }

                        # Store testcase info along with module name and path
                        test_info = {
                            "testcase_name": node.name,
                            "module_name": None,
                            "module_path": None,
                            "attributes": testcase_attributes,
                        }
                        self.test_cases.append(test_info)  # store testcase information

            self.generic_visit(node)

    def __init__(self, test_root_dir, ifc_dir):
        """
        Only need to instantiate object and hierarchy is made available

        :param test_root_dir: entry point for all tests in the system
        :type test_root_dir: str
        :param ifc_dir: entry point for interfaces
        :type ifc_dir: str
        """
        self.test_root_dir = test_root_dir
        self.ifc_dir = ifc_dir
        self.test_groups = self._find_groups_and_cases()
        self.ifc_files = self._find_ifc_files()

    def _find_ifc_files(self):
        """
        _summary_

        :return: create a List of all of the interfaces. The List contains enough information to auto instantiate
        :rtype: List
        """
        ifc_files = {}

        for root, dirs, files in os.walk(self.ifc_dir):
            for file_name in files:
                if file_name.endswith(".py"):
                    module_name = file_name[:-3]  # Remove the .py extension
                    module_path = os.path.join(root, file_name)

                    with open(module_path, "r") as f:
                        try:
                            tree = ast.parse(f.read())
                            visitor = self.ClassVisitor()
                            visitor.visit(tree)
                            class_names = visitor.class_names
                            if class_names:
                                class_name = class_names[0]
                                ifc_files[module_name] = {
                                    "class_name": class_name,
                                    "module_name": module_name,
                                    "module_path": module_path,
                                }
                        except SyntaxError as e:
                            print(f"Error in file {module_path}: {e}")
                            raise

        return ifc_files

    def _find_groups_and_cases(self):
        """
        Walk directory structure and find TestGroups and TestCases

        :return: List of TestGroups which contains a list of TestCases for that group
        :rtype: List
        """
        visitor = self.ClassVisitor()
        for root, dirs, _ in os.walk(self.test_root_dir):
            for dir in dirs:
                sys.path.append(
                    os.path.join(root, dir)
                )  # add test group dirs to python search path
                test_group_dir = os.path.join(root, dir)
                for filename in os.listdir(test_group_dir):
                    if filename.endswith(".py"):
                        with open(os.path.join(test_group_dir, filename), "r") as f:
                            try:
                                tree = ast.parse(f.read())
                                visitor.visit(tree)
                                for (
                                    class_name,
                                    class_info,
                                ) in visitor.test_groups.items():
                                    if class_info["module_name"] is None:
                                        class_info["module_name"] = filename[:-3]
                                        class_info["module_path"] = test_group_dir

                                for testcase in visitor.test_cases:
                                    if testcase["module_name"] is None:
                                        testcase["module_name"] = filename[:-3]
                                        testcase["module_path"] = test_group_dir

                            except SyntaxError as e:
                                print(f"Syntax error in file {filename}: {e}")
                                raise

                for testcase in visitor.test_cases:
                    if visitor.current_group is not None:
                        visitor.current_group["test_cases"].append(testcase)

                visitor.test_cases.clear()

        return visitor.test_groups

    def print_test_groups_all_info(self):
        """
        Loop through hierarchy and print information
        """
        for group_name, group_info in self.test_groups.items():
            print(f"Test Group Name: {group_name}")
            print(f'  Module Name: {group_info["module_name"]}')
            print(f'  Module Path: {group_info["module_path"]}')
            print("  Test Cases:")
            for testcase in group_info["test_cases"]:
                print(f'    Test Case Name: {testcase["testcase_name"]}')
                print(f'    Module Name: {testcase["module_name"]}')
                print(f'    Module Path: {testcase["module_path"]}')
                print("      Attributes:")
                for attribute, value in testcase["attributes"].items():
                    print(f"        {attribute}: {value}")

    def get_total_group_cases(self, group):
        """
        searches for group in test_groups and returns the number of test cases in that group
        """
        for group_name, group_info in self.test_groups.items():
            if group_info["group_attributes"].get("group_id") == group or \
                group == group_info["group_attributes"].get("group_name"):
                return len(group_info["test_cases"])

    def print_test_groups_test_cases(self, group_name=None):
        """
        Print test cases associated for a single test group
        If optional parameter is not included, print all groups

        :param group_name: Name of group, defaults to None
        :type group_name: str, optional
        """

        def print_group_info(group_name, group_info):
            print(f'\nGroup ID: {group_info["group_attributes"]["group_id"]}      Test Group Name: {group_name}')
            for testcase in group_info["test_cases"]:
                print(
                    f'    Test Case ID: {testcase["attributes"]["test_id"]}      Test Case Name: {testcase["testcase_name"]}'
                )

        if group_name is None:
            # If no group name is specified, print all groups.
            for group_name, group_info in self.test_groups.items():
                print_group_info(group_name, group_info)
        else:
            # Otherwise, print the specified group.
            print(self.test_groups)
            group_info = self._find_group(group_name)
            # group_info = self.test_groups.get(group_name)
            if group_info is not None:
                print_group_info(group_name, group_info)
            else:
                print(f"No test group named {group_name} found.")

    def _find_testcase(self, param):
        """
        Search all the test groups and see if param matches the testcase_name or test_id

        :param param: search item
        :type param: str
        :return: group attributes, test case attributes
        :rtype: group, testcase
        """
        for group_name, group_info in self.test_groups.items():
            for testcase in group_info["test_cases"]:
                # Check if the param matches the testcase name or the test_id
                if testcase[
                    "attributes"
                ].get("test_name") == param or param == testcase[
                    "attributes"
                ].get("test_id"):
                    return group_info, testcase
        return None, None

    def _find_group(self, param):
        """
        Search all the test groups and see if param matches the group_name or group_id

        :param param: search item
        :type param: str
        :return: group attributes, 
        :rtype: group
        """
        for group_name, group_info in self.test_groups.items():
            # print(group_name, group_info)
            # for group in group_info["group_attributes"]:
            #     # Check if the param matches the testcase name or the test_id
            if group_info[
                "group_attributes"
            ].get("group_id") == param or param == group_name:
                return group_info
        return None

    def _instantiate_object(self, obj_info, class_name, init_param=None):
        """
        Used to instantiate a TestGroup or TestCase

        :param obj_info: metadata for the object to be instantiated
        :type obj_info: dictionary
        :param class_name: Name of class to instantiate
        :type class_name: str
        :param init_param: Testgroup when instantiating a TestClass, defaults to None when instantiating a TestGroup
        :type init_param: str, optional
        :return: object instance, object module
        :rtype: object instance, object module
        """
        module_name = obj_info.get("module_name")
        module_path = obj_info.get("module_path")

        if not module_name or not module_path:
            print("Module name or module path is missing.")
            return None, None

        try:
            spec = importlib.util.spec_from_file_location(
                module_name, os.path.join(module_path, module_name + ".py")
            )
            if spec is None:
                print(f"Module spec is None for module '{module_name}'.")
                return None, None

            obj_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(obj_module)

            obj_class = getattr(obj_module, class_name)
            if init_param:
                obj_instance = obj_class(init_param)
            else:
                obj_instance = obj_class()

            return obj_instance, obj_module

        except Exception as e:
            print(f"Error occurred during object instantiation: {e}")
            raise

    def instantiate_obj_for_group(self, group_name):
        """
        When given a TestGroup instantiate it and it's associated TestCases

        :param group_name: Name of the TestGroup
        :type group_name: str
        :return: group instance, List of Test Cases
        :rtype: group instance, List of Test Cases
        """
        group_info = self._find_group(group_name)
        # group_info = self.test_groups.get(group_name)
        if not group_info:
            print(f"Test group {group_name} not found.")
            return None, None

        group_instance, _ = self._instantiate_object(
            group_info, group_info["group_name"]
        )
        ifc_instances = self._parse_configure_interfaces(
            group_instance.configure_interfaces
        )
        group_instance.configure_interfaces(*ifc_instances)

        test_case_instances = []
        for testcase_info in group_info["test_cases"]:
            test_case_instance, _ = self._instantiate_object(
                testcase_info, testcase_info["testcase_name"], group_instance
            )
            test_case_instances.append(test_case_instance)

        return group_instance, test_case_instances

    def instantiate_obj_for_testcase(self, testcase_name):
        """
        When given a test case, search the hierarchy for the group it is in,
        instantiate the group and the single test case

        :param testcase_name: Name of Test case
        :type testcase_name: str
        :return: group instance, List with one entry of the test case(list is so upper level code works the same)
        :rtype: group instance, List of single testcase instance
        """
        group_info, testcase_info = self._find_testcase(testcase_name)
        if not group_info or not testcase_info:
            print(f"Test case {testcase_name} not found.")
            return None, None

        group_instance, _ = self._instantiate_object(
            group_info, group_info["group_name"]
        )
        ifc_instances = self._parse_configure_interfaces(
            group_instance.configure_interfaces
        )
        group_instance.configure_interfaces(*ifc_instances)

        test_case_instance, _ = self._instantiate_object(
            testcase_info, testcase_info["testcase_name"], group_instance
        )

        return group_instance, [test_case_instance]

    def _parse_configure_interfaces(self, configure_interfaces_method):
        """
        Pass in a configure_interfaces method from a TestGroup subclass
        ex: def configure_interfaces(self, hc_ifc: HealthCheckIfc):

        search for all of the interface parameters specified in the method, instantiate them, and then
        return a list of the interface objects( used to actually call the configure_interfaces() method)

        :param configure_interfaces_method: _description_
        :type configure_interfaces_method: _type_
        :return: List of interface instances
        :rtype: List
        """
        instances = []

        parameters = (inspect.signature(configure_interfaces_method)).parameters
        for param_name, param in parameters.items():
            class_name = param.annotation.__name__

            if class_name != "self":
                for ifc_file_name, ifc_file_info in self.ifc_files.items():
                    if class_name == ifc_file_info["class_name"]:
                        module_name = ifc_file_info["module_name"]
                        module_path = ifc_file_info["module_path"]

                        try:
                            spec = importlib.util.spec_from_file_location(
                                module_name, module_path
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            if hasattr(module, class_name):
                                class_instance = getattr(module, class_name)()
                                instances.append(class_instance)
                            else:
                                print(
                                    f"Class {class_name} not found in module {module_name}."
                                )
                        except Exception as e:
                            print(
                                f"Error occurred during module instantiation: {module_path} {e}"
                            )
                            raise

        return instances
