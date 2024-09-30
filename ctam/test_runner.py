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
from datetime import datetime, timedelta
from tests.test_case import TestCase
from tests.test_group import TestGroup
from interfaces.functional_ifc import FunctionalIfc
from test_hierarchy import TestHierarchy

from prettytable import PrettyTable
import threading, time
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
from utils.logger_utils import LoggingWriter, LogSanitizer, BuiltInLogSanitizers

from version import __version__


class TestRunner:
    """
    This class is the main controller for test execution
    """

    def __init__(
        self,
        workspace_dir,
        logs_output_dir,
        test_hierarchy,
        test_runner_json_file,
        dut_info_json_file,
        package_info_json_file,
        redfish_uri_config_file,
        redfish_response_messages,
        net_rc,
        single_test_override=None,
        sequence_test_override=None,
        single_group_override=None,
        sequence_group_override=None,
        run_all_tests=None,
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
        self.output_dir = logs_output_dir
        self.workspace_dir = workspace_dir
        self.response_check_name = None
        self.compliance_data = {}
        self.include_tags_set = set()
        self.exclude_tags_set = set()
        self.weighted_scores = {}
        self.normalized_scores = {}
        self.debug_mode = True
        self.console_log = True
        self.progress_bar = False
        self.package_config = package_info_json_file
        self.redfish_response_messages = {}
        self.single_test_override = single_test_override
        # self.logs_output_dir = logs_output_dir
        self.runner_config = self._get_test_runner_config(test_runner_json_file)

        with open(dut_info_json_file) as dut_info_json:
            self.dut_config = json.load(dut_info_json)
            
        with open(redfish_uri_config_file) as redfish_uri:
            self.redfish_uri_config = json.load(redfish_uri)


        self.net_rc = netrc.netrc(net_rc)
        self.sanitize_logs = self.dut_config.get("properties", {}).get("SanitizeLog", False).get("value", False)
        self.words_to_skip = self.get_words_to_skip()

        if redfish_response_messages:
            with open(redfish_response_messages) as resp_file:
                self.redfish_response_messages = json.load(resp_file)
        # use override output directory if specified in test_runner.json, otherwise
        # use TestRuns directory below workspace directory

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
        elif self.runner_config.get("test_sequence", None):
            self.test_sequence = self.runner_config.get("test_sequence", None)
        elif self.runner_config.get("group_sequence", None):
            self.group_sequence = self.runner_config.get("group_sequence", None)
        elif self.runner_config.get("active_test_suite", None):
            test_suite_to_select = self.runner_config.get("active_test_suite", None)
            # Remove the active_test_suite key before selecting the test suite
            # Select the test suite from test_runner_data
            for test_suite in test_suite_to_select:
                selected_test_suite_cases = self.runner_config.get(test_suite)

                if selected_test_suite_cases is not None:
                    # Assign the selected test suite to a Python list
                    for test_case in selected_test_suite_cases:
                        self.test_sequence.append(test_case)
                else:
                    raise Exception(
                        "active_test_suite in test_runner.json specifies missing List"
                    )
        elif run_all_tests:
            self.test_sequence = run_all_tests
    
    def get_words_to_skip(self):
        return [item for sublist in self.net_rc.hosts.values() for item in sublist if isinstance(item, str) if item]

    def _get_test_runner_config(self, test_runner_json_file):
        runner_config = {}
        if os.path.isfile(test_runner_json_file):
            with open(test_runner_json_file) as test_runner_json:
                runner_config = json.load(test_runner_json)
                # self.output_dir = runner_config["output_override_directory"]
                self.response_check_name = runner_config.get("test_uri_response_excel", None)
                
                self.include_tags_set = set(runner_config["include_tags"])
                self.exclude_tags_set = set(runner_config["exclude_tags"])

                self.debug_mode = runner_config["debug_mode"]
                self.console_log = runner_config["console_log"]
                self.progress_bar = runner_config["progress_bar"]
                self.weighted_scores = runner_config.get("weighted_score", None)
                self.normalized_scores = runner_config.get("normalized_score", None)
                if self.normalized_scores:
                    normalized_values = list(self.normalized_scores.values())
                    if sum(normalized_values) != 100:
                        raise Exception("Total Normalized score is not equal to 100. Please check test_runner.json for Normalized score.")
                
                
        else:
            print("[WARNING]: Running CTAM with default setting. If you want to \
                  provide custom setting, Please use test_runner.json config file.")
        return runner_config


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
        # system is up or not
        # If up then establish the connection and the discovery 
        self.cwd = os.path.dirname(os.path.dirname(__file__))
        self.dt = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        test_dir = ""
        if self.include_tags_set  and not self.single_test_override:
            test_dir = f'Tags-{"-".join(self.include_tags_set)}'
            self.output_dir = os.path.join(self.workspace_dir, "TestRuns", test_dir)
       
        self.cmd_output_dir = os.path.join(self.output_dir, "RedfishCommandDetails")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.cmd_output_dir):
            os.makedirs(self.cmd_output_dir)
        dut_logger = LoggingWriter(
            self.cmd_output_dir, self.console_log, testrun_name, "json", self.debug_mode,
            desanitize_log=self.sanitize_logs, words_to_skip=self.words_to_skip
        )
        test_info_logger = LoggingWriter(
            self.output_dir, self.console_log, "TestInfo_"+testrun_name, "json", self.debug_mode,
            desanitize_log=self.sanitize_logs, words_to_skip=self.words_to_skip
        )
        self.score_logger = LoggingWriter(
            self.output_dir, self.console_log, "TestScore_"+testrun_name, "json", self.debug_mode,
            desanitize_log=self.sanitize_logs, words_to_skip=self.words_to_skip
        )
        self.test_result_file = os.path.join(self.output_dir, "TestReport_{}.log".format(self.dt))
        self.test_uri_response_check = None
        if self.response_check_name:
            cwd = "" if self.cwd == "/tmp" else self.cwd
            self.test_uri_response_check = os.path.join(cwd, "workspace", self.response_check_name)

        self.comp_tool_dut = CompToolDut(
            id="actDut",
            config=self.dut_config,
            package_config=self.package_config,
            redfish_uri_config=self.redfish_uri_config,
            test_runner_config=self.runner_config,
            net_rc=self.net_rc,
            debugMode=self.debug_mode,
            console_log=self.console_log,
            logger=dut_logger,
            test_info_logger=test_info_logger,
            test_uri_response_check=self.test_uri_response_check,
            redfish_response_messages=self.redfish_response_messages,
            logger_path=self.output_dir,
            workspace_dir=self.workspace_dir
        )
        self.comp_tool_dut.current_test_name = "Initialization"
        

        self.writer = LoggingWriter(
            self.output_dir, self.console_log, "OCPTV_CTAM_LOGS_", "json", self.debug_mode,
            desanitize_log=self.sanitize_logs, words_to_skip=self.words_to_skip
        )
        tv.config(writer=self.writer)

        self.active_run = tv.TestRun(name="CTAM Test Runner", version=__version__)
        # FIXME: This needs to be fixed after system details 
        # if status_code:
        #     self.active_run.add_log(LogSeverity.INFO, "{}".format(self.system_details))
        # else:
        #     self.active_run.add_log(LogSeverity.FATAL, "{}".format(self.system_details))
        TestCase.SetUpAssociations(self.active_run, self.comp_tool_dut)
        TestGroup.SetUpAssociations(self.active_run, self.comp_tool_dut)
        FunctionalIfc.SetUpAssociations(self.active_run, self.comp_tool_dut)
        
        self.comp_tool_dut.set_up_connection()

        # FIXME: need to standardized details
        # self.system_details, status_code = self.comp_tool_dut.GetSystemDetails()
        # if status_code:
        #     # log system details
        #     timestamp = datetime.now().strftime("%m-%d-%YT%H:%M:%S")
        #     self.system_details_logger = LoggingWriter(
        #         self.output_dir, self.console_log, "SystemDetails", "json", self.debug_mode
        #     )
        #     self.system_details_logger.write(json.dumps(self.system_details))
        
        # self.active_run.start(dut=tv.Dut(id="dut0"))

    def _end(self, run_status, run_result):
        """
        Helper function called at the end of the OCP Testrun

        :param run_status: overall run status
        :type run_status: str
        :param run_result: overall run result
        :type run_result: str
        """
        self.active_run.end(status=run_status, result=run_result)
        tv.config(writer=StdoutWriter())

    def __compliance_level_score(self, testcase):
        
        for tag in self.weighted_scores:
            if tag in testcase.compliance_level:
                testcase.score_weight = self.weighted_scores[tag]
            
    def run(self):
        """
        Public API used to kick of the test suite
        
        :return: status_code, exit_string
        :rtype: int, str 
        """
        try:
            status_code = 0
            self.create_json_configuration()
            if self.progress_bar:
                progress_thread = threading.Thread(target=self.display_progress_bar)
                progress_thread.daemon = True
            data = self.test_hierarchy.get_compliance_test_cases()
            if self.normalized_scores:
                self.comp_data = self.generate_normalized_compliance_data(data, "")
            group_status_set = set()
            group_result_set = set()
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
                    print("Group tags ", group_instance.tags)
                    # group_exc_tags = group_instance.exclude_tags

                    group_status, group_result = self._run_group_test_cases(group_instance, test_case_instances)
                    group_status_set.add(group_status)
                    group_result_set.add(group_result)
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

                    group_status, group_result = self._run_group_test_cases(group_instance, test_case_instances)
                    group_status_set.add(group_status)
                    group_result_set.add(group_result)

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

                    group_status, group_result = self._run_group_test_cases(group_instance, test_case_instances)
                    group_status_set.add(group_status)
                    group_result_set.add(group_result)
                    
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

                    group_status, group_result = self._run_group_test_cases(group_instance, test_case_instances)
                    group_status_set.add(group_status)
                    group_result_set.add(group_result)
                    
            grade = (
                    TestCase.total_compliance_score / TestCase.max_compliance_score * 100
                    if TestCase.max_compliance_score != 0
                    else 0
                )
            
            gtotal = round(grade, 2)

            msg = {
                    "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                    "TotalExecutionTime": str(timedelta(seconds=TestCase.total_execution_time)),
                    "TotalScore": TestCase.total_compliance_score,
                    "MaxComplianceScore": TestCase.max_compliance_score,
                    "Grade": "{}%".format(gtotal),
                    }
            self.score_logger.write(json.dumps(msg))
            self.test_result_data.append(("Total", "", 
                                        timedelta(seconds=TestCase.total_execution_time),
                                        TestCase.max_compliance_score,
                                        TestCase.total_compliance_score,"{}%".format(gtotal)))
            self.generate_domain_test_report()
            if self.weighted_scores:
                self.generate_compliance_level_test_report()
            if self.normalized_scores:
                self.normalized_compliance_level_table()
            self.generate_test_report()
            time.sleep(1)
            if self.progress_bar and self.console_log is False:
                while progress_thread.is_alive():
                    progress_thread.join(10)
                    
            status_code = 1 if group_result_set - {TestResult.PASS} else 0 # if there is any result other than PASS, status code repots failure
            exit_string = "Test execution failed" if group_status_set - {TestStatus.COMPLETE} else "Test execution is complete"
            
        except KeyboardInterrupt:
            status_code, exit_string =  1, "Test interrupted by user (KeyboardInterrupt)"
        except Exception as e:
            exception_details = traceback.format_exc()
            self.active_run.add_log(
                severity=LogSeverity.FATAL, message=exception_details
            )
            msg = {
                "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                "TotalExecutionTime": str(timedelta(seconds=TestCase.total_execution_time)),
                "TotalScore": TestCase.total_compliance_score,
                "MaxComplianceScore": TestCase.max_compliance_score,
                "Grade": "{}%".format(gtotal),
                "FailureReason": exception_details
                }
            self.score_logger.write(json.dumps(msg))
            status_code, exit_string =  1, f"Test failed due to execption: {repr(e)}"
        finally:
            if self.comp_tool_dut:
                self.comp_tool_dut.clean_up()
            self.post_proces_logs(self.writer.log_file)
            return status_code, exit_string
        
        
    def _run_group_test_cases(self, group_instance, test_case_instances):
        """
        for now, create a separate test run for each group. In the event of failures
        that will require smaller test runs to debug and evaluate resolutions

        :param group_instance: instance of the group under test
        :type group_instance: TestGroup
        :param test_case_instances: List of test cases associated with the group
        :type test_case_instances: List[Testcase]]
        :returns: group_status, group_result
        :rtype:  ocptv.output.TestStatus, ocptv.output.TestResult
        """

        group_status = TestStatus.ERROR
        group_result = TestResult.PASS

        try:
            if not self.comp_tool_dut:
                self._start(group_instance.__class__.__name__)
            self.active_run.start(dut=tv.Dut(id=group_instance.__class__.__name__))
            
            group_instance.setup()

            for test_instance in test_case_instances:
                test_inc_tags = test_instance.tags
                tags = list(set(test_inc_tags) | set(group_instance.tags))
                valid = self._is_enabled(
                    self.include_tags_set,
                    tags,
                    self.exclude_tags_set,
                )
                if not valid and not self.single_test_override:
                    msg = f"Test {test_instance.__class__.__name__} skipped due to tags. tags = {test_inc_tags}"
                    skipped_test = self.active_run.add_step(name=f"<{test_instance.test_id} - {test_instance.test_name}> tttttttttttt")
                    skipped_test.start()
                    self.active_run.add_log(severity=LogSeverity.INFO, message=msg)
                    skipped_test.end(status=TestStatus.COMPLETE)
                    continue
                if self.weighted_scores:
                    self.__compliance_level_score(testcase=test_instance)
                # this exception block goal is to ensure test case teardown() is called even if setup() or run() fails
                try:
                    test_starttime = time.perf_counter()
                    # added this step as we need to get the test case name in log post processing
                    test_case_step = self.active_run.add_step(name=f"<{test_instance.test_id} - {test_instance.test_name}>") 
                    test_case_step.start()
                    test_instance.setup()
                    self.comp_tool_dut.current_test_name = test_instance.test_name
                    file_name = "{}_{}".format(test_instance.test_id,
                                                                        test_instance.test_name)
                    logger = LoggingWriter(
                        self.cmd_output_dir, self.console_log, file_name, "json", self.debug_mode,
                        desanitize_log=self.sanitize_logs, words_to_skip=self.words_to_skip
                    )
                    self.comp_tool_dut.logger = logger
                    execution_starttime = time.perf_counter()
                    test_result, status_msg = test_instance.run()
                    # print("status_msg98765", status_msg)
                    # test_result = test_instance.run()
                    if (
                        test_result == TestResult.FAIL
                    ):  # if any test fails, the group fails
                        group_result = TestResult.FAIL
                except:  
                    exception_details = traceback.format_exc()
                    status_msg += " " + exception_details
                    self.active_run.add_log(
                        severity=LogSeverity.FATAL, message=exception_details
                    )
                    test_instance.result = TestResult.FAIL
                    group_result = TestResult.FAIL
                finally:
                    # attempt test cleanup even if test exception raised
                    test_instance.teardown()
                    test_case_step.end(status=TestStatus.COMPLETE)
                    execution_endtime = time.perf_counter()
                    execution_time = round(execution_endtime - execution_starttime, 3)
                    test_instance.execution_time = timedelta(seconds=round(execution_endtime - test_starttime, 3))
                    TestCase.total_execution_time += round(execution_endtime - test_starttime, 3)
                    msg = {
                        "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                        "ExecutionTime": f"{execution_time} seconds",
                        "TestID": test_instance.test_id,
                        "TestName": test_instance.test_name,
                        "TestCaseScoreWeight":test_instance.score_weight,
                        "TestCaseScore": test_instance.score,
                        "TestCaseResult": TestResult(test_instance.result).name,
                        "FailureReason": status_msg + " For more details check Command_Line_Logs.log file"
                    }
                    msg = {key: value for key, value in msg.items() if (key != "FailureReason") or (TestResult(test_instance.result).name == "FAIL")}
                    test_tuple = (test_instance.test_id,
                                                   test_instance.test_name,
                                                   test_instance.execution_time,
                                                   test_instance.score_weight,
                                                   test_instance.score,                                              
                                                   TestResult(test_instance.result).name)
                    self.test_result_data.append(test_tuple)
                    if self.weighted_scores:
                        self.update_weighted_data(test_instance)
                    if self.normalized_scores:
                        self.update_normalized_compliance_data(test_instance)
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

        except KeyboardInterrupt:
            self.active_run.add_log(
                severity=LogSeverity.FATAL, message="Test interrupted by user (KeyboardInterrupt)"
            )
            group_status = TestStatus.ERROR
            group_result = TestResult.FAIL
            
        except (NotImplementedError, Exception) as e:
            exception_details = traceback.format_exc()
            self.active_run.add_log(
                severity=LogSeverity.FATAL, message=exception_details
            )
            msg = {
                "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                "ExecutionTime": f"{execution_time} seconds",
                "TestID": test_instance.test_id,
                "TestName": test_instance.test_name,
                "TestCaseScoreWeight":test_instance.score_weight,
                "TestCaseScore": test_instance.score,
                "TestCaseResult": TestResult(test_instance.result).name,
                "FailureReason": exception_details
            }
            self.score_logger.write(json.dumps(msg))
            group_status = TestStatus.ERROR
            group_result = TestResult.FAIL

        finally:
            # attempt group cleanup even if test exception raised
            group_instance.teardown()
            self._end(group_status, group_result)

            return group_status, group_result

    def get_system_details(self):
        """
        Method to perform System Discovery
        
        :return: status_code, exit_string
        :rtype: int, str 
        """
        try:
            self._start()
            status_code, exit_string = 0, "System discovery is done"
        except KeyboardInterrupt:
            status_code, exit_string = 1, "Test interrupted by user (KeyboardInterrupt)"
        except Exception as e:
            exception_details = traceback.format_exc()
            self.active_run.add_log(
                severity=LogSeverity.FATAL, message=exception_details
            )
            status_code, exit_string = 1,  f"Test failed due to execption: {repr(e)}"
        finally:
            if self.comp_tool_dut:
                self.comp_tool_dut.clean_up()
            return status_code, exit_string
    
    def update_weighted_data(self, test_instance):
        c_level = test_instance.compliance_level
        w_score = self.weighted_scores.get(test_instance.compliance_level, 10)
        execution_time = test_instance.execution_time
        total_test = 1
        test_passed = 1 if TestResult(test_instance.result).name == TestResult.PASS.name else 0
        score_weight = test_instance.score_weight
        score = test_instance.score
        available_testcases = self.test_hierarchy.get_compliance_test_cases()
        grade = 0
        if test_instance.compliance_level in self.weighted_scores:
            self.generate_compliance_data(test_instance, c_level, w_score, available_testcases[c_level], total_test, test_passed, score_weight, score, grade, execution_time)
            
        else:   
            self.generate_compliance_data(test_instance, "L3", self.weighted_scores["L3"], available_testcases["L3"], total_test, test_passed, 0, 0, 0, execution_time)

    def generate_compliance_data(self, test_instance, c_level, l_weight, a_testcases, t_test, t_pass, s_weight, score, grade, e_time):
        
        if c_level not in self.compliance_data:
            
            if s_weight == 0:
                grade = 0
            else:
                grade = round((test_instance.score / test_instance.score_weight * 100), 2)
            self.compliance_data[c_level] = [c_level,
                                            l_weight,
                                            a_testcases,
                                            t_test,
                                            t_pass,
                                            s_weight,
                                            score,
                                            grade,
                                            e_time
                                            ]
        else:
            data = self.compliance_data[c_level]
            sw = data[5] + test_instance.score_weight
            s = data[6] + test_instance.score
            if s_weight == 0:
                grade = 0
            else:
                grade = round((s / sw * 100), 2)
            self.compliance_data[c_level] = [c_level,
                                                l_weight,
                                                a_testcases,
                                                data[3] + t_test,
                                                data[4] + t_pass,
                                                data[5] + s_weight,
                                                data[6]+ score,
                                                grade,
                                                data[8] + e_time
                                                ]

    def generate_normalized_compliance_data(self,  c_data, test_instance):
        comp_data = {}
        for key, value in c_data.items():
            w_score = self.normalized_scores[key]
            d_score = round(w_score/value, 2)

            comp_data[key] = {"Compliance Level":key,
                "Normalized Weight":w_score,
                "TestCases Available":value,
                "Normalized Score":d_score,
                "TestCases Executed":0,
                "TestCases Passed":0,
                "Total Score":0,
                "Max Score":0,
                "Grade":0,
                "Execution Time":timedelta(seconds=0)}
        return comp_data

    def update_normalized_compliance_data(self, test_instance):
        c_level = test_instance.compliance_level
        if c_level in self.comp_data:
            data = self.comp_data[c_level]
            data["TestCases Executed"] += 1
            data["TestCases Passed"] += 1 if TestResult(test_instance.result).name == TestResult.PASS.name else 0
            data["Total Score"] = data["Normalized Score"] * data["TestCases Passed"]
            data["Max Score"] = data["Normalized Score"] * data["TestCases Executed"]
            grade = round(data["TestCases Passed"] / data["TestCases Executed"] * 100, 2)
            data["Execution Time"] += test_instance.execution_time
            data["Grade"] = grade
            self.comp_data[c_level] = data
        else:
            data = self.comp_data["L3"]
            data["TestCases Executed"] += 1
            data["TestCases Passed"] += 1 if TestResult(test_instance.result).name == TestResult.PASS.name else 0
            data["Total Score"] = data["Normalized Score"] * data["TestCases Passed"]
            data["Max Score"] = data["Normalized Score"] * data["TestCases Executed"]
            # grade = round(data["TestCases Passed"] / data["TestCases Executed"] * 100, 2)
            data["Execution Time"] += test_instance.execution_time
            data["Grade"] = 0
            self.comp_data["L3"] = data

    def generate_test_report(self):
        """
        This method is used for creating a tabula format for test result.
        It will have TestID, TestName, Test Score, Test Result, Test Weight and total

        """
        t = PrettyTable(["Test ID", "Test Name", "Execution Time", "TestCase Weight", "Test Score", "Test Result"])
        t.title = f"Test Result -  V {__version__}"
        t.add_rows(self.test_result_data[:len(self.test_result_data) - 1:])
        t.add_row(["", "", "", "", "", ""], divider=True)
        t.add_row(self.test_result_data[-1], divider=True)
        t.align["TestName"] = "l"
        
        with open(self.test_result_file, 'a') as f:
            f.write("\n" + str(t))
        print(t)

    def generate_compliance_level_test_report(self):
        """
        This method is used for creating a tabula format for compliance level test result.
        It will have ComplianceID, ComplianceScore, GroupID, TestCaseID, TestCaseName, WeightedScore, TestScore and TestResult.
        """
        
        if self.weighted_scores:
        
            c_data = dict(sorted(self.compliance_data.items()))
            compliance_values = c_data.values()
            total_test_cases = sum([x[3] for x in compliance_values])
            total_passed_test_cases = sum([x[4] for x in compliance_values])
            total_weight = sum([x[5] for x in compliance_values])
            total_score = sum([x[6] for x in compliance_values])
            total_execution = sum([x[8].total_seconds() for x in compliance_values])
            total_available_testcases = sum([x[2] for x in compliance_values])
            grade = round((total_score / total_weight * 100), 2) if total_weight else 0

            ct = PrettyTable(["Compliance Level", "Level Weight", "TestCases Available", "TestCases Executed", "TestCases Passed", "Total Weight", "Total Score", "Grade", "Total Execution Time"])
            ct.title = "Compliance Level Weighted Report"
            ct.add_rows(c_data.values())
            
            ct.add_row(["","","","","","","","",""], divider=True)
            ct.add_row(["Total", "", total_available_testcases, total_test_cases, total_passed_test_cases, total_weight, total_score, f"{grade}%", timedelta(seconds=total_execution)])
            
            with open(self.test_result_file, 'a') as f:
                f.write("\n" + str(ct))
            print(ct)

    def normalized_compliance_level_table(self):
        data = next(iter(self.comp_data))
        sorted_data = dict(sorted(self.comp_data.items()))
        total_normalized_weight = 0
        total_test_cases_available = 0
        total_normalized_score = 0
        total_test_cases_executed = 0
        total_test_cases_passed = 0
        total_score = 0
        sum_max_score = 0
        total_execution_time = timedelta(seconds=0)

        for key, value in self.comp_data.items():
            total_normalized_weight += value['Normalized Weight']
            total_test_cases_available += value['TestCases Available']
            total_normalized_score += value['Normalized Score']
            total_test_cases_executed += value['TestCases Executed']
            total_test_cases_passed += value['TestCases Passed']
            total_score += value['Total Score']
            sum_max_score += value['Max Score']
            total_execution_time += value['Execution Time']

        grade = round((total_score / sum_max_score * 100), 2) if sum_max_score else 0
        normalized_grade = round((total_test_cases_passed / total_test_cases_available * 100), 2)
        dt = PrettyTable(list(self.comp_data[data].keys()))
        dt.title = "Compliance Level Normalized Weighted Report"
        vals = [d.values() for _,d in sorted_data.items()]
        dt.add_rows(vals)
        dt.add_row(["","","","","","","","", "", ""], divider=True)
        dt.add_row(["Total", total_normalized_weight, total_test_cases_available, total_normalized_score, total_test_cases_executed, total_test_cases_passed, total_score, sum_max_score, f"{grade}%", total_execution_time])
        dt2 = PrettyTable(["TestCases Available", "TestCases Passed", "Grade"])
        dt2.title = "Compliance Level Normalized Weight Overall Report"
        # dt2.add_row(["","", "", ""], divider=True)
        dt2.add_row([total_test_cases_available, total_test_cases_passed, normalized_grade])

        print(dt)
        with open(self.test_result_file, 'a') as f:
            f.write("\n" + str(dt))
        with open(self.test_result_file, 'a') as f:
            f.write("\n" + str(dt2))
        print(dt2)

    def generate_domain_test_report(self):
        """
        This method is used for creating a tabula format for test result for Domain level.
        It will have DomainID, Domain, TComplianceWeight, ComplianceScore, Grade and total

        """
        dt = PrettyTable(["Domain ID", "Domain", "TestCases Available","TestCases Executed", "Testcases Passed", "Total Weight", "Total Score", "Grade", "Total Execution Time"])
        dt.title = "Domain-wise Test Report"

        domain_count = self.test_hierarchy.get_domains()

        executionTimes = [0, 0, 0, 0]
        testCases = [0, 0, 0, 0]
        passedTests = [0, 0, 0, 0]
        compScore = [0, 0, 0, 0]
        compWeight = [0, 0, 0, 0]
        
        for i in range(len(self.test_result_data)-1):
            testID = self.test_result_data[i][0]
            testExecTime = self.test_result_data[i][2].total_seconds()
            testWeight = self.test_result_data[i][3]
            testScore = self.test_result_data[i][4]

            # check for telemetry cases
            if testID.startswith("T"):
                executionTimes[0] += testExecTime
                testCases[0] += 1
                if testScore == testWeight:
                    passedTests[0] += 1
                compWeight[0] += testWeight
                compScore[0] += testScore

            # check for RAS cases
            elif testID.startswith("R"):
                executionTimes[1] += testExecTime
                testCases[1] += 1
                if testScore == testWeight:
                    passedTests[1] += 1
                compWeight[1] += testWeight   
                compScore[1] += testScore

            # check for health check cases
            elif testID.startswith("H"):
                executionTimes[2] += testExecTime
                testCases[2] += 1
                if testScore == testWeight:
                    passedTests[2] += 1
                compWeight[2] += testWeight    
                compScore[2] += testScore

            # check for fw update cases
            elif testID.startswith("F"):
                executionTimes[3] += testExecTime
                testCases[3] += 1
                if testScore == testWeight:
                    passedTests[3] += 1
                compWeight[3] += testWeight    
                compScore[3] += testScore

        grade = [0, 0, 0, 0]
        for j in range(len(compScore)):
            if compWeight[j] != 0:
                grade[j] = compScore[j]/compWeight[j]*100
                grade[j] = round(grade[j], 2)

        dt.add_row(["T", "Telemetry", domain_count["Telemetry"],testCases[0], passedTests[0], 
                    compWeight[0], compScore[0], "{}%".format(grade[0]), timedelta(seconds=executionTimes[0])])
        dt.add_row(["R", "RAS", domain_count["Ras"],testCases[1], passedTests[1], 
                    compWeight[1], compScore[1], "{}%".format(grade[1]), timedelta(seconds=executionTimes[1])])
        dt.add_row(["H", "Health Check", domain_count["HealthCheck"],testCases[2], passedTests[2], 
                    compWeight[2], compScore[2], "{}%".format(grade[2]), timedelta(seconds=executionTimes[2])])
        dt.add_row(["F", "FW Update", domain_count["FWUpdate"],testCases[3], passedTests[3], 
                    compWeight[3], compScore[3], "{}%".format(grade[3]), timedelta(seconds=executionTimes[3])], divider=True)

        executionTimetotal = sum(executionTimes)
        testCasesTotal = sum(testCases)
        passedTestsTotal = sum(passedTests)
        compWeightTotal = sum(compWeight)
        compScoreTotal = sum(compScore)
        gradeTotal = (
                compScoreTotal/ compWeightTotal * 100
                if compWeightTotal != 0
                else 0
            )
        
        gt = round(gradeTotal, 2)

        dt.add_row(["Total", "", "",testCasesTotal, passedTestsTotal,
                   compWeightTotal, compScoreTotal, "{}%".format(gt), timedelta(seconds=executionTimetotal)], divider=True)
        with open(self.test_result_file, 'a') as f:
            f.write("\n" + str(dt))
        print(dt)

    def create_json_configuration(self):
        try:
            # Create 'Configuration' folder inside the CTAM_LOGS_date_time directory if it doesn't exist
            config_files = ["test_runner", "package_info", "dut_info", "redfish_uri_config", "redfish_response_messages"]
            config_folder_path = os.path.join(self.output_dir, "Configuration")
            if not os.path.exists(config_folder_path):
                os.makedirs(config_folder_path)
            sanitizer = LogSanitizer(additional_regex=[
                BuiltInLogSanitizers.CURL, BuiltInLogSanitizers.PASSWORD,
            ])
            def sanitizeData(data):
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, str):
                            data[key] = sanitizer.format(value)
                        elif isinstance(value, (dict, list)):
                            sanitizeData(value)
                elif isinstance(data, list):
                    for item in data:
                        sanitizeData(item)
            resuld_data = {}
            for file_name in os.listdir(self.workspace_dir):
                file_path = os.path.join(self.workspace_dir, file_name)
                if os.path.isfile(file_path):
                   if any(file_name.startswith(f_name) for f_name in config_files):
                       with open(file_path, 'r') as file:
                            data = json.load(file)
                            if self.sanitize_logs:
                                sanitizeData(data)
                            resuld_data[file_name.split(".")[0].replace("_", " ").upper()] = data
            json_file_path = os.path.join(config_folder_path, "ConfigData.json")
            
            with open(json_file_path, 'w') as jsonfile:
                json.dump(resuld_data, jsonfile, indent=4)
                       
        except Exception as e:
            return f"Failed to create Configuration folder or store files: {e}"
    
    def display_progress_bar(self):
        """
        shows a real-time progress bar in the console displaying the percentage of test cases completed.
        """
        with alive_bar(self.total_cases, title= "Progress:", spinner="arrow") as bar:
            count = 0
            while count < self.total_cases:
                temp = count
                count = len(self.test_result_data)
                time.sleep(0.002)
                while temp < count:
                    bar()
                    temp += 1 
                            
                if count == self.total_cases:
                    break

    def post_proces_logs(self, log_path: str = "") -> None:
        try:
            log_data = ""
            with open(log_path, 'r') as log_file:
                log_data = f"[{log_file.read()}]"
                import re
                import ast
                json_data = ast.literal_eval(log_data)
                
                test_start_idx = 0
                test_end_idx = 0
                test_data = []
                file_name = ""
                test_no = 0
                while test_start_idx < len(json_data):
                    if testRunArtifact:= json_data[test_start_idx].get("testRunArtifact", {}):
                        if testRunStart:= testRunArtifact.get("testRunStart", {}): 
                            test_end_idx = test_start_idx
                            while test_end_idx < len(json_data):
                                if testStepArtifact:= json_data[test_end_idx].get("testStepArtifact", {}):
                                    if testStepStart:= testStepArtifact.get("testStepStart", {}): 
                                        check_data = re.findall(r"<(\w+.*)>", testStepStart["name"])  
                                        if check_data:
                                            file_name = check_data[0]
                                            
                                if testRunArtifactInside:= json_data[test_end_idx].get("testRunArtifact", {}): 
                                    if testRunEnd:=testRunArtifactInside.get("testRunEnd", {}):
                                        test_result = testRunEnd["result"]
                                        break
                                test_end_idx += 1
                            test_no += 1
                            test_data.append(("{}_{}_{}".format(test_no, test_result, file_name), json_data[test_start_idx:test_end_idx + 1]))
                            test_start_idx = test_end_idx
                    test_start_idx += 1
                output_path = os.path.join(self.output_dir, "OCPTV_Processed_TestCase_Logs")
                if not os.path.exists(output_path):
                    os.makedirs(output_path)
                for file_name, data in test_data:
                    output_file = os.path.join(output_path, "{}.json".format(file_name))
                    with open(output_file, "w") as f:
                        f.write(json.dumps(data, indent=4))
        except Exception as e:
            exception_details = traceback.format_exc()
            self.active_run.add_log(
                severity=LogSeverity.FATAL, message=exception_details
            )
            # status_code, exit_string = 1,  f"Test failed due to execption: {repr(e)}"