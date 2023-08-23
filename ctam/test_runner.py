"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
from pathlib import Path
import os
import json
import netrc
import platform
import traceback
import logging
import sys
from ocptv.output import LogSeverity, StdoutWriter, Writer
from datetime import datetime
from tests.test_case import TestCase
from tests.test_group import TestGroup
from interfaces.functional_ifc import FunctionalIfc
from test_hierarchy import TestHierarchy
import ocptv.output as tv
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from interfaces.comptool_dut import CompToolDut


class TestRunner:
    """
    This class is the main controller for test execution
    """

    def __init__(
        self,
        test_hierarchy,
        test_runner_json_file,
        dut_info_json_file,
        package_info_json_file,
        redfish_uri_config_file,
        net_rc,
        single_test_override=None,
        sequence_test_override=None,
        single_group_override=None,
    ):
        """
        Init function that handles test execution variations

        :param test_hierarchy: discovered list of test groups and associated test cases
        :type test_hierarchy: TestHierarchy
        :param dut_info_json_file: dut info details json file path
        :type dut_info_json_file: str
        :param package_info_json_file: Package info json file path
        :type package_info_json_file: str
        :param test_runner_json_file: test runner configuration
        :type test_runner_json_file: str
        :param redfish_uri_config_file: redfish uri config json file path
        :type redfish_uri_config_file: str
        :param net_rc: system credentials config file path
        :type net_rc: str
        :param single_test_override: single test to run, defaults to None
        :type single_test_override: str, optional
        :param sequence_test_override: sequence of tests to run, defaults to None
        :type sequence_test_override: list, optional
        :param single_group_override: single group to run, defaults to None
        :type single_group_override: str, optional
        :raises Exception: no tests to run
        """
        self.active_run = None
        self.comp_tool_dut = None
        self.test_hierarchy = test_hierarchy
        self.test_cases = []
        self.test_sequence = []
        self.test_groups = []

        with open(dut_info_json_file) as dut_info_json:
            self.dut_config = json.load(dut_info_json)

        with open(test_runner_json_file) as test_runner_json:
            runner_config = json.load(test_runner_json)

        with open(package_info_json_file) as package_info_json:
            self.package_config = json.load(package_info_json)

        with open(redfish_uri_config_file) as redfish_uri:
            self.redfish_uri_config = json.load(redfish_uri)

        with open(redfish_uri_config_file) as redfish_uri:
            self.redfish_uri_config = json.load(redfish_uri)

        self.net_rc = netrc.netrc(net_rc)

        # use override output directory if specified in test_runner.json, otherwise
        # use TestRuns directory below workspace directory
        self.output_dir = runner_config["output_override_directory"]
        # if out_dir:
        #     self.output_dir = out_dir
        # else:
        #     self.output_dir = os.path.join(os.path.dirname(os.path.dirname(test_runner_json_file)),
        #                                    "workspace","TestRuns")

        # if not os.path.exists(self.output_dir):
        #     os.makedirs(self.output_dir)

        self.include_tags_set = set(runner_config["include_tags"])
        self.exclude_tags_set = set(runner_config["exclude_tags"])

        self.debug_mode = runner_config["debug_mode"]
        self.console_log = runner_config["console_log"]

        # end result is that either test_cases[] or test_groups[] will have values but not both
        # if passed via the command line, then there will only be 1 testcase or 1 testgroup in the list
        if single_test_override != None:
            self.test_cases.append(single_test_override)
        elif single_group_override != None:
            self.test_groups.append(single_group_override)
        elif sequence_test_override != None:
            self.test_sequence = sequence_test_override
        elif runner_config["test_cases"]:
            self.test_cases = runner_config["test_cases"]
        elif runner_config["test_sequence"]:
            self.test_sequence = runner_config["test_sequence"]
        elif runner_config["active_test_suite"]:
            test_suite_to_select = runner_config.get("active_test_suite")
            # Remove the active_test_suite key before selecting the test suite
            del runner_config["active_test_suite"]

            # Select the test suite from test_runner_data
            selected_test_suite = runner_config.get(test_suite_to_select)

            if selected_test_suite is not None:
                # Assign the selected test suite to a Python list
                self.test_groups = selected_test_suite
            else:
                raise Exception(
                    "active_test_suite in test_runner.json specifies missing List"
                )
        else:
            raise Exception(
                "Specify test cases/groups with -t, -g command line options or use test_runner.json"
            )

    def _is_enabled(
        self,
        runner_inc_tags_set,
        tags,
        runner_exc_tags_set,
        # test_exc_tags,
    ):
        """
        Helper function that inspects include and exclude tags to determine if group or test should run
            If exclude_tags list is not empty AND test_case_tag in exclude_tag list, 
            then exclude test case
            Else if include_tags list is not empty AND test_case_tag in include_tags list, 
            then include test case
            Else if include_tags list is not empty AND test_case_tag not in include_tags list, 
            then exclude test case 
            Else if include_tag list is empty 
            then include test case

        :param runner_inc_tags_set: test runner config file include tags, in set for optimization
        :type runner_inc_tags_set: set of List[str]
        :param test_inc_tags: group/test include tags
        :type test_inc_tags: List[str]
        :param runner_exc_tags_set: test runner config file exclude tags, in set for optimization
        :type runner_exc_tags_set: set of List[str]
        :param test_exc_tags: group/test exclude tags
        :type test_exc_tags: List[str]
        :return: true if it should run
        :rtype: bool
        """
        if runner_exc_tags_set and any(tag in runner_exc_tags_set for tag in tags):
            return False

        elif runner_inc_tags_set and any(tag in runner_inc_tags_set for tag in tags):
            return True
        
        elif runner_inc_tags_set and not any(tag in runner_inc_tags_set for tag in tags):
            return False
        elif not runner_inc_tags_set:
            return True
            

    def _start(self, testrun_name="initialization"):
        """
        Helper function called at the start of every OCP test run

        :param testrun_name: name for the testrun
        :type testrun_name: str
        """
        #system is up or not
        # If up then establish the connection and the discovery 
        self.cwd = os.path.dirname(os.path.dirname(__file__))
        self.dt = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        if self.output_dir:
            self.output_dir = os.path.join(
                self.cwd, "workspace", self.output_dir, "TestRuns", testrun_name+"_{}".format(self.dt)
            )
        else:
            self.output_dir = os.path.join(
                self.cwd, "workspace", "TestRuns", testrun_name+"_{}".format(self.dt)
            )
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        dut_logger = LoggingWriter(
            self.output_dir, self.console_log, "CommandDetails_"+testrun_name, "log", self.debug_mode
        )
        self.comp_tool_dut = CompToolDut(
            id="actDut",
            config=self.dut_config,
            package_config=self.package_config,
            redfish_uri_config=self.redfish_uri_config,
            net_rc=self.net_rc,
            debugMode=self.debug_mode,
            logger=dut_logger,

        )
        self.system_details, status_code = self.comp_tool_dut.GetSystemDetails()
        # writer has to be configured prior to TestRun init


        self.writer = LoggingWriter(
            self.output_dir, self.console_log, testrun_name, "json", self.debug_mode
        )
        tv.config(writer=self.writer)

        self.active_run = tv.TestRun(name="CTAM Test Runner", version="1.0")
        if status_code:
            self.active_run.add_log(LogSeverity.INFO, "{}".format(self.system_details))
        else:
            self.active_run.add_log(LogSeverity.FATAL, "{}".format(self.system_details))
        TestCase.SetUpAssociations(self.active_run, self.comp_tool_dut)
        TestGroup.SetUpAssociations(self.active_run, self.comp_tool_dut)
        FunctionalIfc.SetUpAssociations(self.active_run, self.comp_tool_dut)

        self.active_run.start(dut=tv.Dut(id="dut0"))

    def _end(self, run_status, run_result):
        """
        Helper function called at the end of the OCP Testrun

        :param run_status: overall run status
        :type run_status: str
        :param run_result: overall run result
        :type run_result: str
        """
        self.active_run.end(status=run_status, result=run_result)
        self.comp_tool_dut.clean_up()
        tv.config(writer=StdoutWriter())

    def run(self):
        """
        Public API used to kick of the test suite
        """
        if self.test_cases:
            for test in self.test_cases:
                (
                    group_instance,
                    test_case_instances,
                ) = self.test_hierarchy.instantiate_obj_for_testcase(test)

                group_inc_tags = group_instance.tags
                # group_exc_tags = group_instance.exclude_tags
                valid = self._is_enabled(
                    self.include_tags_set,
                    group_inc_tags,
                    self.exclude_tags_set,
                    # group_exc_tags,
                )
                if not valid:
                    print(
                        f"Group1 {group_instance.__class__.__name__} skipped due to tags. tags = {group_inc_tags}"
                    )
                    continue

                self._run_group_test_cases(group_instance, test_case_instances)
        elif self.test_sequence:
            for test in self.test_sequence:
                (
                    group_instance,
                    test_case_instances,
                ) = self.test_hierarchy.instantiate_obj_for_testcase(test)

                group_inc_tags = group_instance.tags
                # group_exc_tags = group_instance.exclude_tags
                valid = self._is_enabled(
                    self.include_tags_set,
                    group_inc_tags,
                    self.exclude_tags_set,
                    # group_exc_tags,
                )
                if not valid:
                    print(
                        f"Group1 {group_instance.__class__.__name__} skipped due to tags. tags = {group_inc_tags}"
                    )
                    continue

                self._run_group_test_cases(group_instance, test_case_instances)

        elif self.test_groups:
            for group in self.test_groups:
                (
                    group_instance,
                    test_case_instances,
                ) = self.test_hierarchy.instantiate_obj_for_group(group)
                group_inc_tags = group_instance.tags
                # group_exc_tags = group_instance.exclude_tags

                valid = self._is_enabled(
                    self.include_tags_set,
                    group_inc_tags,
                    self.exclude_tags_set,
                    # group_exc_tags,
                )

                if not valid:
                    print(
                        f"Group2 {group_instance.__class__.__name__} skipped due to tags. tags = {group_inc_tags}"
                    )
                    continue

                self._run_group_test_cases(group_instance, test_case_instances)

    def _run_group_test_cases(self, group_instance, test_case_instances):
        """
        for now, create a separate test run for each group. In the event of failures
        that will require smaller test runs to debug and evaluate resolutions

        :param group_instance: instance of the group under test
        :type group_instance: TestGroup
        :param test_case_instances: List of test cases associated with the group
        :type test_case_instances: List[Testcase]]
        """

        group_status = TestStatus.ERROR
        group_result = TestResult.PASS

        try:
            if not self.comp_tool_dut:
                self._start(group_instance.__class__.__name__)

            group_instance.setup()

            for test_instance in test_case_instances:
                test_inc_tags = test_instance.tags
                # test_exc_tags = test_instance.exclude_tags

                valid = self._is_enabled(
                    self.include_tags_set,
                    test_inc_tags,
                    self.exclude_tags_set,
                    # test_exc_tags,
                )
                if not valid:
                    msg = f"Test {test_instance.__class__.__name__} skipped due to tags. tags = {test_inc_tags}"
                    self.active_run.add_log(severity=LogSeverity.INFO, message=msg)
                    continue

                # this exception block goal is to ensure test case teardown() is called even if setup() or run() fails
                try:
                    test_instance.setup()
                    test_result = test_instance.run()
                    if (
                        test_result == TestResult.FAIL
                    ):  # if any test fails, the group fails
                        group_result = TestResult.FAIL
                except:
                    exception_details = traceback.format_exc()
                    self.active_run.add_log(
                        severity=LogSeverity.FATAL, message=exception_details
                    )
                    test_instance.result = TestResult.FAIL
                    group_result = TestResult.FAIL
                finally:
                    # attempt test cleanup even if test exception raised
                    test_instance.teardown()

            grade = (
                TestCase.total_compliance_score / TestCase.max_compliance_score * 100
                if TestCase.max_compliance_score != 0
                else 0
            )

            msg = f"Compliance Run completed. Total Score = {TestCase.total_compliance_score:0.2f} out of {TestCase.max_compliance_score:0.2f}, Grade = {grade:0.2f}%"
            self.active_run.add_log(severity=LogSeverity.INFO, message=msg)

            group_status = TestStatus.COMPLETE

        except (NotImplementedError, Exception) as e:
            exception_details = traceback.format_exc()
            self.active_run.add_log(
                severity=LogSeverity.FATAL, message=exception_details
            )

            group_status = TestStatus.ERROR
            group_result = TestResult.FAIL

        finally:
            # attempt group cleanup even if test exception raised
            group_instance.teardown()
            self._end(group_status, group_result)
    def get_system_details(self):
        self._start()
        pass

class LoggingWriter(Writer):
    """
    Helper class registers python logger with OCP logger to be used for file output etc

    :param Writer: OCP Writer super class
    :type Writer:
    """

    def __init__(self, output_dir, console_log, testrun_name,extension_name,  debug):
        """
        Initialize file logging parameters

        :param output_dir: location of log file
        :type output_dir: str
        :param console_log: true if desired to print to console as well as log
        :type console_log: bool
        :param testrun_name: name for current testrun
        :type testrun_name: str
        :param debug: if true, log LogSeverity.DEBUG messages
        :type debug: bool
        """
        # Create a logger
        self.logger = logging.getLogger(testrun_name)
        self.debug = debug

        # Set the level for this logger. This means that unless specified otherwise, all messages
        # with level INFO and above will be logged.
        # If you want to log all messages you can use logging.DEBUG
        self.logger.setLevel(logging.INFO)

        # Create formatters and add them to the handlers
        # formatter = logging.Formatter("%(message)s")

        # Create a file handler that logs messages to a file
        dt = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        file_name_tmp = "/{}_{}.{}".format(testrun_name, dt, extension_name)
        self.file_handler = logging.FileHandler(output_dir + file_name_tmp)
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(self.file_handler)

        if console_log:
            # Create a console handler that logs messages to the console
            self.console_handler = logging.StreamHandler()
            self.console_handler.setLevel(logging.INFO)
            self.console_handler.setFormatter(JsonFormatter())
            self.logger.addHandler(self.console_handler)

    def write(self, buffer: str):
        """
        Called from the OCP framework for logging messages.  Use debug switch to filter
        LogSeverity.DEBUG messages.

        :param buffer: _description_
        :type buffer: str
        """
        if not self.debug:
            if '"severity": "debug"' in buffer.lower():
                return

        self.logger.info(buffer)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        """
        :Description:                       Format method for formatting data into json output

        :param JSON Dict record:		    Dict object for Log JSON Data

        :returns:                           JSON object with indent 4
        :rtype                              JSON Dict
        """
        msg = json.loads(getattr(record, "msg", None))
        return json.dumps(msg, indent=4)
