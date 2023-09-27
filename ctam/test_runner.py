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
#from unittest import runner
from ocptv.output import LogSeverity, StdoutWriter, Writer
from datetime import datetime
from tests.test_case import TestCase
from tests.test_group import TestGroup
from interfaces.functional_ifc import FunctionalIfc
from test_hierarchy import TestHierarchy

from prettytable import PrettyTable
import threading, time
from queue import Queue
from alive_progress import alive_bar

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
        sequence_group_override=None,
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
        self.group_sequence = []
        self.test_result_data = []
        self.total_cases = 0

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
        self.response_check_name = runner_config.get("test_uri_response_excel", None)
        
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
        self.progress_bar = runner_config["progress_bar"]

        # end result is that either test_cases[] or test_groups[] will have values but not both
        # if passed via the command line, then there will only be 1 testcase or 1 testgroup in the list
        if single_test_override != None:
            self.test_cases.append(single_test_override)
        elif single_group_override != None:
            self.test_groups.append(single_group_override)
        elif sequence_test_override != None:
            self.test_sequence = sequence_test_override
        elif sequence_group_override != None:
            self.group_sequence = sequence_group_override
        elif runner_config["test_cases"]:
            self.test_cases = runner_config["test_cases"]
        elif runner_config["test_sequence"]:
            self.test_sequence = runner_config["test_sequence"]
        elif runner_config["group_sequence"]:
            self.group_sequence = runner_config["group_sequence"]
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
        self.cmd_output_dir = os.path.join(self.output_dir, "RedfishCommandDetails")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.cmd_output_dir):
            os.makedirs(self.cmd_output_dir)
        dut_logger = LoggingWriter(
            self.cmd_output_dir, self.console_log, "RedfishCommandDetails_"+testrun_name, "json", self.debug_mode
        )
        test_info_logger = LoggingWriter(
            self.output_dir, self.console_log, "TestInfo_"+testrun_name, "json", self.debug_mode
        )
        self.score_logger = LoggingWriter(
            self.output_dir, self.console_log, "TestScore_"+testrun_name, "json", self.debug_mode
        )
        self.test_result_file = os.path.join(self.output_dir, "TestReport_{}.log".format(self.dt))
        self.test_uri_response_check = None
        if self.response_check_name:
            self.test_uri_response_check = os.path.join(self.cwd, "workspace", self.response_check_name)

        self.comp_tool_dut = CompToolDut(
            id="actDut",
            config=self.dut_config,
            package_config=self.package_config,
            redfish_uri_config=self.redfish_uri_config,
            net_rc=self.net_rc,
            debugMode=self.debug_mode,
            console_log=self.console_log,
            logger=dut_logger,
            test_info_logger=test_info_logger,
            test_uri_response_check=self.test_uri_response_check

        )
        self.comp_tool_dut.current_test_name = "Initialization"
        # FIXME: This needs to be fixed
        # self.system_details, status_code = self.comp_tool_dut.GetSystemDetails()
        # writer has to be configured prior to TestRun init


        self.writer = LoggingWriter(
            self.output_dir, self.console_log, "OCPTV_"+testrun_name, "json", self.debug_mode
        )
        tv.config(writer=self.writer)

        self.active_run = tv.TestRun(name="CTAM Test Runner", version="1.0")
        # FIXME: This needs to be fixed after system details 
        # if status_code:
        #     self.active_run.add_log(LogSeverity.INFO, "{}".format(self.system_details))
        # else:
        #     self.active_run.add_log(LogSeverity.FATAL, "{}".format(self.system_details))
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
        try:
            if self.progress_bar:
                progress_thread = threading.Thread(target=self.display_progress_bar)
                progress_thread.daemon = True

            if self.test_cases:
                if self.progress_bar and self.console_log is False:
                        self.total_cases = len(self.test_cases)
                        progress_thread.start()

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
                if self.progress_bar and self.console_log is False:
                        self.total_cases = len(self.test_sequence)
                        progress_thread.start()
                        
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
                    if self.progress_bar and self.console_log is False:
                        self.total_cases = len(test_case_instances)
                        progress_thread.start()
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
            elif self.group_sequence:
                # get total cases in group sequence from test hierarchy
                tc_group = []
                for g in self.group_sequence:
                    tc_group.append(self.test_hierarchy.get_total_group_cases(g))

                self.total_cases = sum(tc_group)
                if self.progress_bar and self.console_log is False:
                    progress_thread.start()

                for group in self.group_sequence:
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
            grade = (
                    TestCase.total_compliance_score / TestCase.max_compliance_score * 100
                    if TestCase.max_compliance_score != 0
                    else 0
                )
            
            gtotal = round(grade, 2)

            msg = {
                    "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                    "TotalScore": TestCase.total_compliance_score,
                    "MaxComplianceScore": TestCase.max_compliance_score,
                    "Grade": "{}%".format(gtotal),
                    }
            self.score_logger.write(json.dumps(msg))
            self.test_result_data.append(("Total Score", "", TestCase.total_compliance_score, 
                                        TestCase.max_compliance_score,"{}%".format(gtotal)))
            self.generate_test_report()
            self.generate_domain_test_report()
            time.sleep(2)
            if self.progress_bar and self.console_log is False:
                while progress_thread.is_alive():
                    progress_thread.join(10)
        except KeyboardInterrupt:
            sys.exit(1)
        
        
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
                    self.comp_tool_dut.current_test_name = test_instance.test_name
                    file_name = "RedfishCommandDetails_{}_{}".format(test_instance.test_id,
                                                                        test_instance.test_name)
                    logger = LoggingWriter(
                        self.cmd_output_dir, self.console_log, file_name, "json", self.debug_mode
                    )
                    self.comp_tool_dut.logger = logger
                    execution_starttime = time.perf_counter()
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
                    execution_endtime = time.perf_counter()
                    execution_time = round(execution_endtime - execution_starttime, 3)
                    msg = {
                        "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                        "ExecutionTime": execution_time,
                        "TestID": test_instance.test_id,
                        "TestName": test_instance.test_name,
                        "TestCaseScoreWeight":test_instance.score_weight,
                        "TestCaseScore": test_instance.score,
                        "TestCaseResult": TestResult(test_instance.result).name
                    }
                    self.test_result_data.append((test_instance.test_id,
                                                   test_instance.test_name,
                                                   test_instance.score_weight,
                                                   test_instance.score,                                              
                                                   TestResult(test_instance.result).name))
                    self.score_logger.write(json.dumps(msg))

            grade = (
                TestCase.total_compliance_score / TestCase.max_compliance_score * 100
                if TestCase.max_compliance_score != 0
                else 0
            )

            grt = round(grade, 2)

            msg = f"Compliance Run completed. Total Score = {TestCase.total_compliance_score:0.2f} out of {TestCase.max_compliance_score:0.2f}, Grade = {grt:0.2f}%"
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

    def generate_test_report(self):
        """
        This method is used for creating a tabula format for test result.
        It will have TestID, TestName, Test Score, Test Result, Test Weight and total

        """
        #print(self.test_result_data)
        t = PrettyTable(["TestID", "TestName", "TestScoreWeight", "TestScore", "TestResult"])
        t.title = "Test Result"
        t.add_rows(self.test_result_data[:len(self.test_result_data) - 1:])
        t.add_row(["", "", "", "", ""], divider=True)
        t.add_row(["", "","Compliance Score",
                   "Total Test Score", "Grade"], divider=True)
        t.add_row(self.test_result_data[-1], divider=True)
        t.align["TestName"] = "l"
        
        with open(self.test_result_file, 'a') as f:
            f.write(str(t))
        print(t)

    def generate_domain_test_report(self):
        """
        This method is used for creating a tabula format for test result for Domain level.
        It will have DomainID, Domain, TComplianceWeight, ComplianceScore, Grade and total

        """
        dt = PrettyTable(["DomainID", "Domain", "ComplianceWeight", "ComplianceScore", "Grade"])
        dt.title = "Domain-wise Test Report"

        compScore = [0, 0, 0, 0]
        compWeight = [0, 0, 0, 0]

        for i in range(len(self.test_result_data)-1):
            testID = self.test_result_data[i][0]
            testWeight = self.test_result_data[i][2]
            testScore = self.test_result_data[i][3]

            # check for telemetry cases
            if testID.startswith("T"):
                compWeight[0] += testWeight
                compScore[0] += testScore

            # check for RAS cases
            elif testID.startswith("R"):
                compWeight[1] += testWeight   
                compScore[1] += testScore

            # check for health check cases
            elif testID.startswith("H"):
                compWeight[2] += testWeight    
                compScore[2] += testScore

            # check for fw update cases
            elif testID.startswith("F"):
                compWeight[3] += testWeight    
                compScore[3] += testScore

        grade = [0, 0, 0, 0]
        for j in range(len(compScore)):
            if compWeight[j] != 0:
                grade[j] = compScore[j]/compWeight[j]*100
                grade[j] = round(grade[j], 2)

        dt.add_row(["T", "Telemetry", compWeight[0], compScore[0], "{}%".format(grade[0])])
        dt.add_row(["R", "RAS", compWeight[1], compScore[1], "{}%".format(grade[1])])
        dt.add_row(["H", "Health Check", compWeight[2], compScore[2], "{}%".format(grade[2])])
        dt.add_row(["F", "FW Update", compWeight[3], compScore[3], "{}%".format(grade[3])], divider=True)

        compWeightTotal = sum(compWeight)
        compScoreTotal = sum(compScore)
        gradeTotal = (
                compScoreTotal/ compWeightTotal * 100
                if compWeightTotal != 0
                else 0
            )
        
        gt = round(gradeTotal, 2)

        dt.add_row(["", "Overall", 
                   compWeightTotal, compScoreTotal, "{}%".format(gt)], divider=True)
        with open(self.test_result_file, 'a') as f:
            f.write("\n" + str(dt))
        print(dt)

    def update_report(self, out_q):
        """
        updates the current value of executed number of test cases and passes it to progress_bar()
        param: queue object
        """
        current = 0
        while current < self.total_cases:
            temp2 = current
            current = len(self.test_result_data)
            if current == temp2 + 1:
                # print("current value=", current)
                out_q.put(current)


    def display_progress_bar(self):
        """
        prints a progress bar in the console displaying the percentage of test cases completed.
        """
        # print("total cases in progress_bar=", self.total_cases)


        with alive_bar(self.total_cases, title= "Progress:", spinner="arrow") as bar:
            count = 0
            while count < self.total_cases:
                temp = count
                #count = in_q.get()
                count = len(self.test_result_data)

                if count == temp + 1:
                    bar()
                            
                if count == self.total_cases:
                    break


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
        
    def log(self, msg: str):
        """
        Called from the OCP framework for logging messages. This method is a wrapper
        of the "write" method to add timestamp to a message.

        :param msg: Message to be logged
        :type msg: str
        """
        json_msg = {
                    "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                    "Message": msg
        }

        self.write(json.dumps(json_msg))


class JsonFormatter(logging.Formatter):
    def format(self, record):
        """
        :Description:                       Format method for formatting data into json output

        :param JSON Dict record:		    Dict object for Log JSON Data

        :returns:                           JSON object with indent 4
        :rtype                              JSON Dict
        """
        msg = json.loads(getattr(record, "msg", None))
        f_msg = json.dumps(msg, indent=4) 
        return f_msg + ","
