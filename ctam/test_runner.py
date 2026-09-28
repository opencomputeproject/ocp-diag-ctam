"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
from pathlib import Path
import os
import re
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
from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet


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
COUNTER = 0

class _NullActiveRun:
    def add_log(self, *args, **kwargs):
        pass

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
        default_config_path,
        net_rc,
        consolidate = None,
        single_test_override=None,
        sequence_test_override=None,
        single_group_override=None,
        sequence_group_override=None,
        run_all_tests=None,
        spec_version=None,
        test_runner_spec_version=None,
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
        self.consolidate_data = []
        self.total_cases = 0
        self.overall_compliance_grade = 0
        self.test_summary_path = None
        self.overall_test_result_dict = None
        self.t_execution_time = 0
        self.output_dir = logs_output_dir
        self.workspace_dir = workspace_dir
        self.consolidate = consolidate
        self.response_check_name = None
        self.compliance_data = {}
        self.consolidate_compliance_data = {}
        self.inside = False
        self.include_tags_set = set()
        self.exclude_tags_set = set()
        self.weighted_scores = {}
        self.normalized_scores = {}
        self.score_max = 0
        self.t_executed = 0
        self.t_pass = 0
        self.test_cache = {}
        self.test_all_cache = []
        self.debug_mode = True
        self.console_log = True
        self.progress_bar = False
        self.package_config = package_info_json_file
        self.redfish_response_messages = {}
        self.default_config_path = default_config_path
        self.show_spec_bindings = False
        self.measurements = {}
        self.writer = None
        self.active_run = None
    
        if self.default_config_path:
            self._show_spec_bindings()
            self.show_spec_bindings = True

        self.test_runner_spec_version = test_runner_spec_version
        
        self.single_test_override = single_test_override
        runner_config = self._get_test_runner_config(test_runner_json_file) 
        runner_config_file = test_runner_json_file
        self.spec_version = spec_version 
        self.latest_spec_version = self.get_latest_spec_version()

        with open(dut_info_json_file) as dut_info_json:
            self.dut_config = json.load(dut_info_json)
            
        with open(redfish_uri_config_file) as redfish_uri:
            self.redfish_uri_config = json.load(redfish_uri)


        self.net_rc = netrc.netrc(net_rc)
        self.sanitize_logs = self.dut_config.get("properties", {}).get("SanitizeLog", {}).get("value", False)
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
        elif runner_config.get("test_sequence", None):
            self.test_sequence = runner_config.get("test_sequence", None)
        
        elif runner_config.get("group_sequence", None):
            self.group_sequence = runner_config.get("group_sequence", None)
        elif runner_config.get("active_test_suite", None):
            test_suite_to_select = runner_config.get("active_test_suite", None)
            # Remove the active_test_suite key before selecting the test suite
            # Select the test suite from test_runner_data
            for test_suite in test_suite_to_select:
                selected_test_suite_cases = runner_config.get(test_suite)

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
            net_rc=self.net_rc,
            debugMode=self.debug_mode,
            console_log=self.console_log,
            logger=dut_logger,
            test_info_logger=test_info_logger,
            test_uri_response_check=self.test_uri_response_check,
            redfish_response_messages=self.redfish_response_messages,
            default_config_path=self.default_config_path,
            logger_path=self.output_dir,
            workspace_dir=self.workspace_dir,
            output_dir=self.output_dir
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
            if not testcase.compliance_level:
                testcase.score_weight = self.weighted_scores["L3"]

            elif tag in testcase.compliance_level:
                testcase.score_weight = self.weighted_scores[tag]
            
    def run(self):
        """
        Public API used to kick of the test suite
        
        :return: status_code, exit_string
        :rtype: int, str 
        """
        exit_string = ""  # always defined
        self._executed_any_test = False
        if self.active_run is None:
            self.active_run = _NullActiveRun()

        try:
            status_code = 0
            exit_string = "Test execution failed"
            gtotal = 0
            self.create_json_configuration()
            if self.progress_bar:
                progress_thread = threading.Thread(target=self.display_progress_bar)
                progress_thread.daemon = True
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
                    if group_instance is None:
                        print(f"Test case {test} not found, skipping.", flush=True)
                        continue

                    for testcase in test_case_instances:
                        self.normalize_testcase_metadata(testcase)

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

                """
                1.Initialize previous_test_result:
                    The variable previous_test_result is initialized as True, representing the result of the previous test.
                2.Iterate Over Test Sequence:
                    Loop through self.test_sequence using enumerate to process each test case in sequence.
                3.Check for "PROF" Test:
                    If the current test is "PROF", get the previous test from the sequence (prev_test).
                    If the result of the previous test (previous_test_result) is "FAIL", log the message and exit the loop.
                    Otherwise, continue to the next iteration.
                4.Update Previous Test Result:
                    Assign the result of the current test (group_result.value) to previous_test_result.

                """
                previous_test_result = True       
                for index, test in enumerate(self.test_sequence):
                    if test == "PROF":
                        prev_test = self.test_sequence[index - 1]

                        if previous_test_result == "FAIL":
                            msg = f"PROF encountered at index {index}... result of previous test: {prev_test} -> {previous_test_result}"
                            self.active_run.add_log(severity=LogSeverity.INFO, message=msg)
                            break
                        else:
                            continue
                                            
                    (
                        group_instance,
                        test_case_instances,
                    ) = self.test_hierarchy.instantiate_obj_for_testcase(test)
                    if group_instance is None:
                        print(f"Test case {test} not found, skipping.", flush=True)
                        continue

                    for testcase in test_case_instances:
                        self.normalize_testcase_metadata(testcase)

                    group_inc_tags = group_instance.tags
                    # group_exc_tags = group_instance.exclude_tags
                    group_status, group_result = self._run_group_test_cases(group_instance, test_case_instances)
                    previous_test_result = group_result.value
    
                    group_status_set.add(group_status)
                    group_result_set.add(group_result)

            elif self.test_groups:
                for group in self.test_groups:
                    (
                        group_instance,
                        test_case_instances,
                    ) = self.test_hierarchy.instantiate_obj_for_group(group)

                    for testcase in test_case_instances:
                        self.normalize_testcase_metadata(testcase)

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

                    for testcase in test_case_instances:
                        self.normalize_testcase_metadata(testcase)
                        
                    group_inc_tags = group_instance.tags
                    # group_exc_tags = group_instance.exclude_tags

                    group_status, group_result = self._run_group_test_cases(group_instance, test_case_instances)
                    group_status_set.add(group_status)
                    group_result_set.add(group_result)
                    

            # Generate a summary of testcases
            if self.test_cache:
                self.generate_test_score_summary()
            
                    
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
            
            # Generate various reports
            self.generate_full_log_from_summary()
            
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
            if hasattr(self, 'active_run'):
                self.active_run.add_log(
                    severity=LogSeverity.FATAL, message=exception_details
                )
            if hasattr(self, 'score_logger'):
                msg = {
                    "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
                    "TotalExecutionTime": str(timedelta(seconds=TestCase.total_execution_time)),
                    "TotalScore": TestCase.total_compliance_score,
                    "MaxComplianceScore": TestCase.max_compliance_score,
                    "Grade": "{}%".format(gtotal),
                    "FailureReason": exception_details
                    }
                self.score_logger.write(json.dumps(msg))
            status_code, exit_string = 1, f"Test failed due to execption: {repr(e)}"
        finally:
            if self.comp_tool_dut:
                self.comp_tool_dut.clean_up()
            if hasattr(self, 'writer'):
                self.post_proces_logs(self.writer.log_file)
            if not self._executed_any_test:
                log_msg = (
                    "No runnable CTAM tests were executed for this "
                    "platform; result is NA."
                )
                exit_string = "No applicable tests"
                if hasattr(self, 'active_run') and self.active_run:
                    self.active_run.add_log(severity=LogSeverity.INFO, message=log_msg)
                else:
                    print(f"INFO: {log_msg}")

            return status_code, exit_string
        
    def consolidate_run(self):
        """
        Consolidates test results from multiple JSON files and generates a final consolidated report.
        """
        try:
            status_code = 0
            exit_string = "Test consolidation completed successfully"
            
            if self.consolidate:
                self.inside = True
                
                # Generate a timestamped log filename for better tracking
                timestamp = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
                log_filename = f"TestReport_consolidated_{timestamp}.log"
                output_file  = os.path.join(self.output_dir, log_filename)
                
                # Generate a timestamped json filename for better tracking
                log_json_name = f"TestScore_consolidated_{timestamp}.json"
                consolidated_output_json  = os.path.join(self.output_dir, log_json_name)
                
                # Initialize variables for summary calculations
                self.test_result_file = output_file
                
                # Consolidate all test score JSONs into one
                log_paths = self.consolidate  #self.consolidate` contains the list of folders
                self.get_consolidated_test_scores(log_paths, consolidated_output_json)  # Now cleans and consolidates the JSON files
                
                with open(consolidated_output_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                filtered_data_dict = {}
                
                for entry in data:
                    if "TestID" in entry and "ExecutionTime" in entry:
                        try:
                            # Convert execution time string to float
                            exec_time_sec = float(entry["ExecutionTime"].split()[0]) # Extract time in seconds
                            entry["ExecutionTime"] = exec_time_sec  # Replace with float
                            filtered_data_dict[entry["TestID"]] = entry
                        except ValueError:
                            print(f"Skipping entry with invalid ExecutionTime: {entry}")
                    else:
                        print(f"Skipping incomplete entry: {entry}")
                        
                if not filtered_data_dict:
                    raise Exception("No valid test data found in the consolidated JSON files.")

                # Generate test score summary JSON from the filtered data
                self.generate_test_score_summary(filtered_data_dict, self.test_score_data)
                
                # Generate the full log from the summary
                self.generate_full_log_from_summary()
                        
                print(f"Consolidated log is present at: {self.test_result_file}")
        
        except Exception as e:
            status_code, exit_string = 1, f"Test consolidation failed due to exception: {repr(e)}"
        
        return status_code, exit_string

    def get_consolidated_test_scores(self,log_paths, consolidated_output_json):
        """
        Retrieves JSON files matching the TestScore* filename from given folder paths,
        consolidates into a single JSON file.
        """
        self.test_score_data = []

        for folder_path in log_paths:
            if not os.path.exists(folder_path):
                print(f"Warning: Folder not found - {folder_path}")
                continue

            for file in os.listdir(folder_path):
                full_path = os.path.join(folder_path, file)
                if file.startswith("TestScore") and file.endswith(".json"):
                    try:
                        data = self.load_fixed_json(full_path)  # Use the fixed JSON loader

                        if isinstance(data, list):
                            # Filter and keep only objects that have 'TestID'
                            filtered_data = [entry for entry in data if "TestID" in entry]
                            self.test_score_data.extend(filtered_data)
                            
                        # Append only valid test case entries having single test result
                        elif isinstance(data, dict) and "TestID" in data:
                            self.test_score_data.append(data)
                            
                    except Exception as e:
                        print(f"Error reading {full_path}: {e}")
                        
        # Check for Duplicate TestID's
        filtered_list = []
        # Dictionary to store result for unique TestID
        filtered_data = {}
        # For the repeated TestID's create only one entry with result as FAIL if
        # any one of the result in the repeated TestID fails.
        for record in self.test_score_data:
            test_id = record['TestID']
            # convert the execution time to float
            exec_time = float(record['ExecutionTime'].split()[0])
            test_result = record['TestCaseResult']

            #if the test ID not available before then add it
            if test_id not in filtered_data:
                filtered_data[test_id] = record
            else:
                # If the current record has FAIL and has higher execution time then replace it
                existing_record = filtered_data[test_id]
                existing_exec_time = float(existing_record['ExecutionTime'].split()[0])
                if (test_result == "FAIL"):
                    if existing_record['TestCaseResult'] != "FAIL" or exec_time > existing_exec_time:
                        filtered_data[test_id] = record
                else:
                    if existing_record['TestCaseResult'] != "FAIL" and exec_time > existing_exec_time:
                        filtered_data[test_id] = record

        # Convert the dictionary values back to a list and assign it back to test_score_data
        self.test_score_data = list(filtered_data.values())

        # Save the consolidated cleaned JSON data into a single JSON file
        with open(consolidated_output_json, "w", encoding="utf-8") as out_f:
            json.dump(self.test_score_data, out_f, indent=4)

        print(f"Consolidated JSON saved at: {consolidated_output_json}")
    
    def load_fixed_json(self, file_path):
        """
        Reads and fixes improperly formatted JSON files before parsing.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()

            if not content:
                print(f"Warning: {file_path} is empty!")
                return []
            
            # Fix JSON format: Ensure it starts with '[' and ends with ']'
            if not content.startswith("["):
                content = "[" + content
            if not content.endswith("]"):
                content += "]"
            
            # Remove trailing commas inside the JSON
            content = re.sub(r",\s*}", "}", content)  # Remove trailing commas in objects
            content = re.sub(r"},\s*]", "}]", content)  # Remove trailing comma before closing bracket
            
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in {file_path}: {e}")
            return []

       
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
        global COUNTER
        group_status = TestStatus.ERROR
        group_result = TestResult.PASS

        try:
            if not self.comp_tool_dut:
                if not self.spec_version:
                    if self.test_runner_spec_version: 
                        spec_version = Version(self.test_runner_spec_version)
                    else:
                        spec_version, _ = self.get_latest_spec_version()
                    self.initialize_spec_path(spec_version)
                self._start(group_instance.__class__.__name__)
            self.active_run.start(dut=tv.Dut(id=group_instance.__class__.__name__))
            
            group_instance.setup()

            for test_instance in test_case_instances:
                status, error_msg = self.resolve_and_load_spec_version(test_instance) 
                test_inc_tags = test_instance.tags
                tags = list(set(test_inc_tags) | set(group_instance.tags))
                valid = self._is_enabled(
                    self.include_tags_set,
                    tags,
                    self.exclude_tags_set,
                ) 
                if not valid and not self.single_test_override:
                    msg = f"Test {test_instance.__class__.__name__} skipped due to tags. tags = {test_inc_tags}"
                    skipped_test = self.active_run.add_step(name=f"<{test_instance.test_id} - {test_instance.test_name}>")
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
                    file_name = "{}_{}_{}".format(COUNTER, test_instance.test_id,
                                                                        test_instance.test_name)
                    COUNTER += 1
                    logger = LoggingWriter(
                        self.cmd_output_dir, self.console_log, file_name, "json", self.debug_mode,
                        desanitize_log=self.sanitize_logs, words_to_skip=self.words_to_skip
                    )
                    self.comp_tool_dut.logger = logger
                    execution_starttime = time.perf_counter()
                    failure_reason = ""
                    if not status:
                        msg = f"{test_instance.__class__.__name__} skipped due to :{error_msg}"
                        self.active_run.add_log(severity=LogSeverity.ERROR, message=msg)
                        failure_reason = "spec version not supported"
                    else:
                        # Inject measurements into all test cases
                        test_instance.measurements = self.measurements
                        test_result, failure_reason = test_instance.run()
                        self._executed_any_test = True
                        if (
                            test_result == TestResult.FAIL
                        ):  # if any test fails, the group fails
                            group_result = TestResult.FAIL
                except:  
                    exception_details = traceback.format_exc()
                    failure_reason = exception_details
                    self.active_run.add_log(
                        severity=LogSeverity.FATAL, message=exception_details
                    )
                    test_instance.result = TestResult.FAIL
                    group_result = TestResult.FAIL
                finally:
                    # attempt test cleanup even if test exception raised
                    try:
                        test_instance.teardown()
                    except Exception as e:
                        exception_details = traceback.format_exc()
                        self.active_run.add_log(
                            severity=LogSeverity.FATAL, message=exception_details
                        )
                        failure_reason += f" Teardown failed due to exception: {repr(e)}"   
                        test_instance.result = TestResult.FAIL
                           
                    test_case_step.end(status=TestStatus.COMPLETE)

                    test_id = test_instance.test_id
                    activation_time = getattr(test_instance, "activation_time", 0.0) 
                    activation_status = getattr(test_instance, "activation_status", False) 
                    activation_failure_reason = getattr(test_instance, "activation_failure_reason", "")
                    staging_time = getattr(test_instance, "staging_time", 0.0)
                    staging_status = getattr(test_instance, "staging_status", False)
                    staging_failure_reason = getattr(test_instance, "staging_failure_reason", "")
                    test_status = getattr(test_instance, "test_status", False)
                    self.measurements[test_id] = { 
                        "activation_time": activation_time,
                        "activation_status": activation_status,
                        "activation_failure_reason": activation_failure_reason,
                        "staging_time": staging_time,
                        "staging_status": staging_status,
                        "staging_failure_reason": staging_failure_reason,
                        "test_status": test_status
                    }
                    print(f"{self.measurements}")     
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
                        "FailureReason": failure_reason + " For more details check Command_Line_Logs.log file"
                    }
                    msg = {key: value for key, value in msg.items() if (key != "FailureReason") or (TestResult(test_instance.result).name == "FAIL")}
                    test_tuple = (test_instance.test_id,
                                                   test_instance.test_name,
                                                   test_instance.execution_time,
                                                   test_instance.score_weight,
                                                   test_instance.score,                                              
                                                   TestResult(test_instance.result).name)
                    self.test_result_data.append(test_tuple)
                                           
                    # Removing duplicates and storing the latest result
                    self.filter_and_update_test_results(test_instance, execution_time, failure_reason)
                    
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
    
    
    def filter_and_update_test_results(self, test_instance, execution_time, failure_reason=None):
        """
        Filter and update the test result cache with the current test instance based on result and execution time.
        """
        
        test_id = test_instance.test_id
        test_result = TestResult(test_instance.result).name

        # Construct the result entry
        result_entry = {
            "TestID": test_id,
            "TestName": test_instance.test_name,
            "ExecutionTime": execution_time,
            "TestCaseScoreWeight": test_instance.score_weight,
            "TestCaseScore": test_instance.score,
            "TestCaseResult": test_result,
            "FailureReason": failure_reason
        }
        # Append all test data for detailed logging
        self.test_all_cache.append(result_entry)
        
        #if the test ID not available before then add it
        if test_id not in self.test_cache:
            self.test_cache[test_id] = result_entry
        else:
            # If the current record has FAIL and has higher execution time then replace it
            existing = self.test_cache[test_id]
            existing_exec_time = existing["ExecutionTime"]
            new_exec_time = execution_time

            if test_result == "FAIL":
                if existing["TestCaseResult"] != "FAIL" or new_exec_time > existing_exec_time:
                    self.test_cache[test_id] = result_entry
            else:
                if existing["TestCaseResult"] != "FAIL" and new_exec_time > existing_exec_time:
                    self.test_cache[test_id] = result_entry

          
    def generate_test_score_summary(self, filtered_data_dict=None, test_score_data=None):
        """
        Generate a detailed JSON report summarizing test execution metrics, scores, and compliance levels for all test cases.
        """

        try:
            # Generate a timestamped json filename for better tracking
            timestamp = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
            json_name = f"TestScore_Summary_{timestamp}.json"
            self.test_summary_path = os.path.join(self.output_dir, json_name)

            #default structure for the test_score_summary.json
            default_report = {
                            "domain_summary": {
                                "domains": {
                                    
                                }
                            },
                            "compliance_level_weighted": {
                                "levels": {
                                    
                                }
                            },
                            "compliance_level_normalized": {
                                "levels": {
                                   
                                }
                            },
                            "Overall_Compliance": {
                                
                            },
                            "test_results": []
                        }
            
            # Load existing data if file exists
            if os.path.exists(self.test_summary_path):
                with open(self.test_summary_path, "r") as f:
                    try:
                        test_report = json.load(f)
                    except json.JSONDecodeError:
                        test_report = default_report
            else:
                test_report = default_report
            
            
            # If consolidate and inside are True, use filtered_data_dict for the consolidated report.
            # Otherwise, use the test_cache for normal flow.
            if self.consolidate and self.inside:
                self.overall_test_result_dict = filtered_data_dict
            else:
                self.overall_test_result_dict = self.test_cache
                
            # Process each test entry from test_cache dictionary
            for testid, test_data in self.overall_test_result_dict.items():
                test_id = test_data["TestID"]
                t_score = test_data["TestCaseScore"]
                execution_time = test_data["ExecutionTime"]
                test_result = test_data["TestCaseResult"]
                self.score_max += test_data["TestCaseScore"]
                self.t_executed += 1
                self.t_pass += 1 if test_result == "PASS" else 0
                self.t_execution_time += execution_time
                
                group_instance, test_case_instances = self.test_hierarchy.instantiate_obj_for_testcase(test_id)
                            
                for test_instance in test_case_instances:
                    self.normalize_testcase_metadata(test_instance)

                    if self.weighted_scores:
                        self.__compliance_level_score(testcase=test_instance)

                    self.domain_data(test_instance, t_score, execution_time, test_result, test_report)
                    self.compliance_level_weighted_data(test_instance, t_score, execution_time, test_result, test_report)
                    self.compliance_level_normalized_data(test_instance, t_score, execution_time, test_result, test_report)
                    
            # Ensure all expected compliance levels are included
            self.add_missing_compliance_levels(test_report)
            
            # overall test result summary
            self.test_result_summary(test_report, test_score_data)
            
            # Write the final updated report to the JSON file  
            with open(self.test_summary_path, "w") as f:
                json.dump(test_report, f, indent=4)
            print(f"Test_Score_Summary written to: {self.test_summary_path}")

        except Exception as e:
            print(f"Failed to  write Test_Score_Summary.json: {e}")
    
        
    def domain_data(self, test_instance, t_score, execution_time, test_result, test_report):
        """
        Update domain-wise test metrics in the test_score_summary.json report based on the current test execution.
        """

        domain_count = self.test_hierarchy.get_domains()
        
        # Find the domain name that matches the test ID prefix
        prefix = test_instance.test_id[0]
        
        matched_domain_name = None
        for domain_name in domain_count:
            if domain_name.startswith(prefix):
                matched_domain_name = domain_name
                break
            
        # If match found, update domain_summary
        if matched_domain_name:
            key = prefix
            # Get or create the domain dict inside test_report
            if key not in test_report["domain_summary"]["domains"]:
                test_report["domain_summary"]["domains"][key] = {
                    "domain_name": matched_domain_name,
                    "testcases_available": domain_count[matched_domain_name],
                    "testcases_executed": 0,
                    "testcases_passed": 0,
                    "total_weight": 0,
                    "total_score": 0,
                    "grade": 0,
                    "total_execution_time": 0
                }
                
            # Now update the domain summary with test results
            domain = test_report["domain_summary"]["domains"][key]
            domain["testcases_executed"] += 1
            domain["testcases_passed"] += 1 if test_result == "PASS" else 0
            domain["total_weight"] += test_instance.score_weight
            domain["total_score"] += t_score
            domain["grade"] = round((domain["total_score"] / domain["total_weight"] * 100), 2) if domain["total_weight"] != 0 else 0
            domain["total_execution_time"] += execution_time
            
        else:
            print(f"Warning: No matching domain found for test ID {test_instance.test_id}")
                        
    def compliance_level_weighted_data(self, test_instance, t_score, execution_time, test_result, test_report):
        """
        Update compliance-level metrics in the test_score_summary.json based on current test execution.
        """

        compliance_level = test_instance.compliance_level if test_instance.compliance_level in self.weighted_scores else "L3"
        available_testcases = self.test_hierarchy.get_compliance_test_cases(self.resolve_compliance_level)
        
        # Initialize the level if not present in report
        levels = test_report["compliance_level_weighted"]["levels"]
        if compliance_level not in levels:
            levels[compliance_level] = {
                "level_weight": 0,
                "testcases_available": 0,
                "testcases_executed": 0,
                "testcases_passed": 0,
                "total_weight": 0,
                "total_score": 0,
                "grade": 0,
                "total_execution_time": 0
            }
            
        # Update compliance-level metrics
        compliance = levels[compliance_level]
        compliance["level_weight"] = self.weighted_scores.get(compliance_level, 0)
        compliance["testcases_available"] = available_testcases.get(compliance_level, 0)
        compliance["testcases_executed"] += 1
        compliance["testcases_passed"] += 1 if test_result == "PASS" else 0
        compliance["total_weight"] += test_instance.score_weight
        compliance["total_score"] += t_score
        compliance["grade"] = round((compliance["total_score"] / compliance["total_weight"] * 100), 2) if compliance["total_weight"] != 0 else 0
        compliance["total_execution_time"] += execution_time
        
    def compliance_level_normalized_data(self, test_instance, t_score, execution_time, test_result, test_report):
        """
        Update normalized compliance-level metrics and overall compliance in the test_score_summary.json 
        based on current test execution.
        """
        compliance_level = test_instance.compliance_level if test_instance.compliance_level in self.weighted_scores else "L3"
        domain_count = self.test_hierarchy.get_domains()
        available_testcases = self.test_hierarchy.get_compliance_test_cases(self.resolve_compliance_level)
        
        # Initialize the level if not already present
        c_levels = test_report["compliance_level_normalized"]["levels"]
        if compliance_level not in c_levels:
            c_levels[compliance_level] = {
                "normalized_weight": 0,
                "testcases_available": 0,
                "normalized_score": 0,
                "testcases_executed": 0,
                "testcases_passed": 0,
                "total_weight": 0,
                "total_score": 0,
                "grade": 0,
                "execution_time": 0
            }
        
        #Update normalized compliance-level metrics
        normalized = c_levels[compliance_level]
        normalized["normalized_weight"] = self.normalized_scores.get(compliance_level, 0)
        normalized["testcases_available"] = self.test_hierarchy.get_compliance_test_cases(self.resolve_compliance_level).get(compliance_level, 0)

        normalized["normalized_score"] = round(normalized["normalized_weight"] / normalized["testcases_available"], 2) if normalized["testcases_available"] != 0 else 0
        normalized["testcases_executed"] += 1
        normalized["testcases_passed"] += 1 if test_result == "PASS" else 0
        normalized["total_weight"] = round(normalized["normalized_score"] * normalized["testcases_executed"], 2)
        normalized["total_score"] = round(normalized["normalized_score"] * normalized["testcases_passed"], 2)
        normalized["grade"] = round(normalized["testcases_passed"] / normalized["testcases_executed"] * 100, 2) if normalized["testcases_executed"] != 0 else 0
        normalized["execution_time"] += execution_time
        
        
        # Initialize Overall_Compliance if not present
        if "Overall_Compliance" not in test_report:
            test_report["Overall_Compliance"] = {
                "testcases_available": 0,
                "testcases_executed": 0,
                "testcases_passed": 0,
                "Overall_Compliance_Level_Weighted_Grade": 0
            }

        # Update overall compliance metrics
        overall_compliance = test_report["Overall_Compliance"]
        overall_compliance["testcases_available"] = sum(domain_count.values())
        overall_compliance["testcases_executed"] = self.t_executed
        overall_compliance["testcases_passed"] = self.t_pass
        
        # Calculate total weighted score
        total_sum = sum(available_testcases.get(compliance_level, 0) * self.weighted_scores.get(compliance_level, 0) for compliance_level in available_testcases)
        overall_compliance["Overall_Compliance_Level_Weighted_Grade"] = round((self.score_max / total_sum) * 100, 2) if total_sum != 0 else 0
     
    def test_result_summary(self, test_report, test_score_data):
        """
        Append the current test result from the test cache to the overall test result summary.
        """
        test_result_all_summary = test_score_data if self.consolidate and self.inside else self.test_all_cache
        result_summary = test_report["test_results"]
        result_summary.extend(test_result_all_summary)
        
        
    def add_missing_compliance_levels(self, test_report):
        """
        Ensure all expected compliance levels are included (e.g.,L0, L1, L2, L3).
        """         
        domain_summary = test_report["domain_summary"]["domains"]
        all_domains = self.test_hierarchy.get_domains()
        for domain, value in all_domains.items():
            prefix = domain[0]  # T, F, R, etc.
            if prefix not in domain_summary:
                domain_summary[prefix] = {
                    "domain_name": domain,
                    "testcases_available": value,
                    "testcases_executed": 0,
                    "testcases_passed": 0,
                    "total_weight": 0,
                    "total_score": 0,
                    "grade": 0,
                    "total_execution_time": 0
                }
                      
        available_testcases = self.test_hierarchy.get_compliance_test_cases(self.resolve_compliance_level)
        weighted_levels = test_report["compliance_level_weighted"]["levels"]
        normalized_levels = test_report["compliance_level_normalized"]["levels"]
        
        if self.weighted_scores:
            for comp_level, weight in self.weighted_scores.items():
                # Add missing weighted level
                if comp_level not in weighted_levels:
                    # Use .get() — weighted_score keys like "Others" may not map to any test case
                    num_available = available_testcases.get(comp_level, 0)
                    weighted_levels[comp_level] = {
                        "level_weight": weight,
                        "testcases_available": num_available,
                        "testcases_executed": 0,
                        "testcases_passed": 0,
                        "total_weight": 0,
                        "total_score": 0,
                        "grade": 0,
                        "total_execution_time": 0
                    }
        if self.normalized_scores:
            for comp_level, weight in self.normalized_scores.items():
                # Add missing normalized level
                if comp_level not in normalized_levels:
                    available_normaized_testcases = self.test_hierarchy.get_compliance_test_cases(self.resolve_compliance_level).get(comp_level, 0)

                    norm_score = round(weight / available_normaized_testcases, 2) if available_normaized_testcases else 0
                    normalized_levels[comp_level] = {
                        "normalized_weight": weight,
                        "testcases_available": available_normaized_testcases,
                        "normalized_score": norm_score,
                        "testcases_executed": 0,
                        "testcases_passed": 0,
                        "total_weight": 0,
                        "total_score": 0,
                        "grade": 0,
                        "execution_time": 0
                    }
        
                
    def generate_full_log_from_summary(self):
        """
        Generate a complete test report log file with all tables using the summary JSON file.
        """
        try:
            if not self.test_summary_path:
                raise FileNotFoundError("Test summary JSON file not found.")

            # Load the summary JSON data
            with open(self.test_summary_path, "r") as f:
                test_report = json.load(f)
                
            # --- Domain Table ---
            domain_headers = [
                "Domain ID", "Domain", "TestCases Available", "TestCases Executed",
                "Testcases Passed", "Total Weight", "Total Score", "Grade", "Total Execution Time"
            ]
            domain_title = "Domain-wise Test Report"

            domain_data = test_report["domain_summary"]["domains"]
            domain_rows = []
            d_total = {"available":0, "executed":0, "passed":0, "weight":0, "score":0, "time":0}
            for dom_id, data in sorted(domain_data.items()):
                domain_rows.append([
                    dom_id, data["domain_name"], data["testcases_available"], data["testcases_executed"],
                    data["testcases_passed"], data["total_weight"], data["total_score"],
                    f"{data['grade']}%", self.seconds_to_time(data["total_execution_time"])
                ])
                d_total["available"] += data["testcases_available"]
                d_total["executed"] += data["testcases_executed"]
                d_total["passed"] += data["testcases_passed"]
                d_total["weight"] += data["total_weight"]
                d_total["score"] += data["total_score"]
                d_total["time"] += data["total_execution_time"]

            d_gradeTotal = round(d_total['score'] / d_total['weight'] * 100, 2) if d_total['weight'] else 0

            domain_total_row = [
                "Total", "", d_total["available"], d_total["executed"], d_total["passed"],
                d_total["weight"], d_total["score"], f"{d_gradeTotal}%", self.seconds_to_time(d_total["time"])
            ]
            # Print the domain table
            self.print_pretty_table(domain_title, domain_headers, domain_rows, total_row=domain_total_row)
            
            
            # --- Compliance Weighted Table ---
            weighted_headers = [
                "Compliance Level", "Level Weight", "TestCases Available",
                "TestCases Executed", "TestCases Passed", "Total Weight",
                "Total Score", "Grade", "Total Execution Time"
            ]
            weighted_title = "Compliance Level Weighted Report"
            weighted = test_report["compliance_level_weighted"]["levels"]
            weighted_rows = []
            w_total = {"available":0, "executed":0, "passed":0, "weight":0, "score":0, "time":0}

            for level, data in sorted(weighted.items()):
                weighted_rows.append([
                    level, data["level_weight"], data["testcases_available"], data["testcases_executed"],
                    data["testcases_passed"], data["total_weight"], data["total_score"],
                    data["grade"], self.seconds_to_time(data["total_execution_time"])
                ])
                w_total["available"] += data["testcases_available"]
                w_total["executed"] += data["testcases_executed"]
                w_total["passed"] += data["testcases_passed"]
                w_total["weight"] += data["total_weight"]
                w_total["score"] += data["total_score"]
                w_total["time"] += data["total_execution_time"]
                
            w_gradeTotal = round(w_total['score'] / w_total['weight'] * 100, 2) if w_total['weight'] else 0
            
            weighted_total_row = [
                "Total", "", w_total["available"], w_total["executed"], w_total["passed"],
                w_total["weight"], w_total["score"], f"{w_gradeTotal}%", self.seconds_to_time(w_total["time"])
            ]
            # Print the weighted compliance table
            self.print_pretty_table(weighted_title, weighted_headers, weighted_rows, total_row=weighted_total_row)
            
            
            # --- Compliance Normalized Table ---
            normalized_headers = [
                "Compliance Level", "Normalized Weight", "TestCases Available",
                "Normalized Score", "TestCases Executed", "TestCases Passed",
                "Total Weight","Total Score", "Grade", "Execution Time"
            ]
            normalized__title = "Compliance Level Normalized Weighted Report"
            normalized = test_report["compliance_level_normalized"]["levels"]
            normalized_rows = []
            n_total = {"n_weight":0, "available":0, "n_score": 0, "executed":0, "passed":0, "weight":0, "score":0, "time":0}

            for level, data in sorted(normalized.items()):
                normalized_rows.append([
                    level, data["normalized_weight"], data["testcases_available"], data["normalized_score"],
                    data["testcases_executed"], data["testcases_passed"],
                    data["total_weight"],data["total_score"], data["grade"],
                    self.seconds_to_time(data["execution_time"])
                ])
                n_total["n_weight"] += data["normalized_weight"]
                n_total["available"] += data["testcases_available"]
                n_total["n_score"] += data["normalized_score"]
                n_total["executed"] += data["testcases_executed"]
                n_total["passed"] += data["testcases_passed"]
                n_total["weight"] += data["total_weight"]
                n_total["score"] += data["total_score"]
                n_total["time"] += data["execution_time"]
            
            n_gradeTotal = round(n_total['score'] / n_total['weight'] * 100, 2) if n_total['weight'] else 0

            normalized_total_row = [
                "Total", n_total["n_weight"], n_total["available"], n_total["n_score"], n_total["executed"], n_total["passed"],
                round(n_total["weight"], 2), round(n_total["score"], 2), f"{n_gradeTotal}%", self.seconds_to_time(n_total["time"])
            ]
            # Print the normalized compliance table
            self.print_pretty_table(normalized__title, normalized_headers, normalized_rows, total_row=normalized_total_row)
           
            
            # --- Overall Compliance Table ---
            overall_comp  = test_report["Overall_Compliance"]
            overall_headers = [
                "TestCases Available", "TestCases Executed", "TestCases Passed",
                "Overall Compliance Level Weighted Grade"
            ]
            overall_title = "Overall Compliance Report"
            overall_rows = [[
                overall_comp["testcases_available"], overall_comp["testcases_executed"],
                overall_comp["testcases_passed"], overall_comp["Overall_Compliance_Level_Weighted_Grade"]
            ]]
            #Print the overall compliance table
            self.print_pretty_table(overall_title, overall_headers, overall_rows)
            
            
            # --- Test Results Table ---
            test_headers = [
                "Test ID", "Test Name", "Execution Time", "TestCase Weight", "Test Score", "Test Result", "Failure Reason"
            ]
            test_title = f"Test Result -  V {__version__}"
            
            test_rows = []
            t_total_weight = 0
            t_total_score = 0

            for test in test_report["test_results"]:
                exec_t = 0.0
                # If the execution time is a string, convert it to float
                if isinstance(test["ExecutionTime"], str):
                    try:
                        exec_t = float(test["ExecutionTime"].split()[0])
                    except Exception as e:
                        print(f"Failed to parse ExecutionTime: {test['ExecutionTime']} ({e})")
                        exec_t = 0.0
                else:
                    exec_t = test["ExecutionTime"]
                failure_reason = test.get("FailureReason", "")  
                # Clean up escaped newlines/tabs
                failure_reason = failure_reason.replace("\\n", " ").replace("\\t", " ")
                words = failure_reason.split()
                failure_reason = " ".join(words[:8])  # keep only first 8 words
                if len(words) > 8:
                    failure_reason += " ..."  # optional: indicate truncation 
                test_rows.append([
                    test["TestID"], test["TestName"], self.seconds_to_time(exec_t),
                    test["TestCaseScoreWeight"], test["TestCaseScore"], test["TestCaseResult"],
                    failure_reason
                ])
                
                # Accumulate total weight, and score
                t_total_weight += test["TestCaseScoreWeight"]
                t_total_score += test["TestCaseScore"]
                
        
            # If consolidate and inside are both True, calculate the total grade and total execution time for the consolidated report; 
            # otherwise, use the existing logic.
            if self.consolidate and self.inside:
                t_grade_total = round(t_total_score / t_total_weight * 100, 2) if t_total_weight != 0 else 0
            else:
                t_grade_total = round(TestCase.total_compliance_score / TestCase.max_compliance_score * 100, 2) if TestCase.max_compliance_score != 0 else 0
            
            c_weight = t_total_weight if self.consolidate and self.inside else TestCase.max_compliance_score    
            score_t = t_total_score if self.consolidate and self.inside else TestCase.total_compliance_score
            
            test_total_row = ["Total", "", self.seconds_to_time(self.t_execution_time), c_weight, score_t, f"{t_grade_total}%", ""]
            
            self.print_pretty_table(test_title, test_headers, test_rows, total_row=test_total_row) # Print the test results table

            
            print(f"Full log report generated at: {self.test_result_file}")

        except Exception as e:
            print(f"Failed to generate full log report: {e}")
            
            
    def seconds_to_time(self, seconds):
        """
        Convert seconds to a formatted timedelta string.
        """
        return str(timedelta(seconds=round(seconds, 3)))
    
    
    # --- Generic Table Printer ---
    def print_pretty_table(self, title, headers, rows, total_row=None):
        """
        Generic method to create, print, and write a PrettyTable to the log file.
        """
        try:
            table = PrettyTable(headers)
            table.title = title

            for row in rows:
                table.add_row(row)

            if total_row:
                table.add_row(["" for _ in headers], divider=True)
                table.add_row(total_row)

            if "Failure Reason" in headers:
                table.align["Failure Reason"] = "l"
    
            print(table)
            
            # Write the table to the test result file
            with open(self.test_result_file, "a") as f:
                f.write(str(table) + "\n\n")
                
        except Exception as e:   
            print(f"Failed to print table '{title}': {e}")
  
  
    def get_system_details(self):
        """
        Method to perform System Discovery
        
        :return: status_code, exit_string
        :rtype: int, str 
        """
        status_code = -1
        exit_string = ""

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
    

    def create_json_configuration(self):
        try:
            # Create 'Configuration' folder inside the CTAM_LOGS_date_time directory if it doesn't exist
            config_files = ["test_runner", "package_info", "dut_info", "redfish_uri_config", "redfish_response_messages"]
            config_folder_path = os.path.join(self.output_dir, "Configuration")
            if not os.path.exists(config_folder_path):
                os.makedirs(config_folder_path)
            sanitizer = LogSanitizer(additional_regex=[
                BuiltInLogSanitizers.CURL, BuiltInLogSanitizers.PASS_WD,
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

    def get_latest_spec_version(self):
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "json_spec", "input")

        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Base path not found: {base_path}")

        spec_folders = [
            d for d in os.listdir(base_path)
            if d.startswith("spec_") and os.path.isdir(os.path.join(base_path, d))
        ]

        if not spec_folders:
            raise FileNotFoundError("No spec_* folders found under json_spec/input")

        versions = []
        for folder in spec_folders:
            version_str = folder.replace("spec_", "")
            try:
                versions.append(Version(version_str))
            except InvalidVersion:
                print(f"Skipping invalid spec folder: {folder}")

        if not versions:
            raise FileNotFoundError("No valid spec_* folders found under json_spec/input")

        versions_sorted = sorted(versions)
        latest_version = versions_sorted[-1]
        all_versions = [str(v) for v in versions_sorted]

        return latest_version, all_versions
    
    def is_supported_version(self, test_instance, version):
        spec_support = getattr(test_instance, "spec_versions", None)
        if isinstance(spec_support, list):
            support_versions = [Version(v) for v in spec_support]
            if version in support_versions:
                return True
        elif isinstance(spec_support, str):
            sign, support = spec_support.split()
            spec_support = Version(support)
            expr = f"({version} {sign} {spec_support})"
            return eval(expr)

    def resolve_and_load_spec_version(self, test_instance): 
        """
        Determines and loads the appropriate specification version for the test case
        based on inputs from the command line, the test_runner.json file, and the
        versions supported by the test case itself.

        Decision logic:
        1. If no spec version is provided via command line or test_runner.json:
            → Use and load the latest available spec version.
        2. If a spec version is provided via the command line:
            → Give it first priority.
            → Validate it against all known versions and the test case’s supported versions.
            → Run if valid and supported; otherwise, fail with an appropriate message.
        3. If no command-line spec is passed but a version exists in test_runner.json:
            → Validate it against the available and supported versions.
            → Load and run if valid; otherwise, fail.

        Args:
            test_instance (object): The test case instance whose spec compatibility 
                                    and version need to be resolved.

        Returns:
            tuple:
                (bool, str or None)
                - bool: Indicates whether the spec version was successfully resolved and loaded.
                - str or None: Error message if resolution fails, None otherwise.
        """
        spec_support = getattr(test_instance, "spec_versions", None)
        spec_version = self.spec_version  
        spec_version = Version(spec_version) if spec_version else None
        result = False
        if spec_version:
            result = self.is_supported_version(test_instance, spec_version)
            
        test_runner_spec_version = Version(self.test_runner_spec_version) if self.test_runner_spec_version else None
        latest_version, all_versions_str = self.get_latest_spec_version()
        all_versions = [Version(v) for v in all_versions_str]

        # Case 1: If spec is missing from both test runner json and cmd line, then go with the latest version
        if (not test_runner_spec_version and not spec_version):
            self.initialize_spec_path(latest_version)
            print(f"\033[31mPicking the latest version since not specified in test_runner.json and not passed through the command line: {latest_version}\033[0m")
            return  True, None
        
        # Case 2: Giving first preference to spec version passed through the command line
        if spec_version:
            # Validate version 
            is_valid_version = spec_version in all_versions and spec_version <= latest_version
            if not is_valid_version:
                return False, "The spec version passed through the command line is not a valid version"

            if spec_support:
                if result:
                    print("################### running with spec_version :", spec_version)
                    return  True, None
                else:
                    return False, "The spec version passed through the cmd is not supported by the test case"
            else: 
                print("################### running with spec_version :", spec_version)
                return  True, None
                
        # take the test_runner_spec_version  if the spec version is not passed through cmd line
        is_valid_version = test_runner_spec_version in all_versions and test_runner_spec_version <= latest_version 
        if not is_valid_version:
            return False, "The spec version in test_runner.json is not a valid version"

        if self.is_supported_version(test_instance, test_runner_spec_version):
            self.initialize_spec_path(test_runner_spec_version)
            print("########## Running the test with the spec version specified in the test runner :", test_runner_spec_version)
            return  True, None  
        else:
            return  False, "The version provided in the test_runner.json is not supported by the test case"


    def initialize_spec_path(self, spec_version=None):
        """
        Initializes and sets the default path for the given specification version.

        Args:
            spec_version (str, optional): The specification version to initialize.
        
        Notes:
            - Ensures the spec bindings are displayed only once.
            - Only prepares the path reference; it does not create or modify any files.
        """
        self.default_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "json_spec", "input", f"spec_{spec_version}")
        self.default_config_path = self.default_config_path.replace('/tmp/', '') if self.default_config_path.startswith('/tmp/') else self.default_config_path
        if not self.show_spec_bindings:
            self._show_spec_bindings()
            self.show_spec_bindings = True
        
    def _show_spec_bindings(self):
        json_file_path = os.path.join(
            self.default_config_path,
            "spec_bindings.json"   
        )

        if os.path.exists(json_file_path):
            with open(json_file_path, "r") as f:
                content = json.load(f)
            print("\n========== OCP SPEC BINDINGS ==========")
            print(json.dumps(content, indent=4))
            print("=================================\n")
        else:
            print(f"File not found: {json_file_path}")

    def resolve_compliance_level(self, compliance_level):
        """
        Supports:
            "L1"

        and:

            {
                ">=1.0,<1.2": "L2",
                ">=1.2": "L1"
            }
        """

        # Simple static compliance
        if isinstance(compliance_level, str):
            return compliance_level

        # Dynamic compliance mapping
        if isinstance(compliance_level, dict):
            if self.spec_version:
                version = Version(self.spec_version)
            elif self.test_runner_spec_version:
                version = Version(self.test_runner_spec_version)
            else:
                version, _ = self.get_latest_spec_version()

            for expr, level in compliance_level.items():
                if version in SpecifierSet(expr):
                    return level

        return "L3"  

    def normalize_testcase_metadata(self, testcase):

        resolved_level = self.resolve_compliance_level(
            testcase.compliance_level
        )
        testcase.compliance_level = resolved_level
        # Remove stale compliance tags
        testcase.tags = [
            tag for tag in testcase.tags
            if tag not in ["L0", "L1", "L2", "L3"]
        ]

        # Inject resolved compliance tag
        testcase.tags.append(resolved_level)     
            
