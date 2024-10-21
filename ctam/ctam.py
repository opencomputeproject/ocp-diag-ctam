# Copyright (c) NVIDIA CORPORATION
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import os
import progressbar
import sys
import traceback
import json
from pathlib import Path
from datetime import datetime
# until the folder structure gets fixed to a more pip/setuptools oriented format
# we need to manually adjust the path so that running the main script's imports work
sys.path.append(str(Path(__file__).resolve().parent))

from test_hierarchy import TestHierarchy
from test_runner import TestRunner

from sys import exit
from version import __version__

from utils.logger_utils import RedirectOutput

def parse_args():
    """
    :Description:                       Parse command line arguments

    :returns:                           Parsed arguments list
    :rtype:                             List
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--testcase",
        help="Runs a single test case. Overrides test_runner.json in the workspace",
        type=str,
    )
    parser.add_argument(
        "-test_seq",
        "--testcase_sequence",
        help="Runs no of test cases with given sequence",
        nargs="+",
    )
    parser.add_argument(
        "-group_seq",
        "--group_sequence",
        help="Runs no of groups with given sequence",
        nargs="+",
    )
    parser.add_argument("-s", "--Suite", help="Run full ACT Suite", action="store_true")

    parser.add_argument(
        "-g",
        "--group",
        help="Run tests for a single group. Overrides test_runner.json in the workspace",
        type=str,
    )

    parser.add_argument("-d", "--Discovery", help="Perform System Discovery", action="store_true")
    
    # parser.add_argument("-x", "--Discovery", help="Perform System Discovery", action="store_true")

    parser.add_argument(
        "-l",
        "--list",
        help="List all test cases. If combined with -G then list all cases of the chosen group ",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--workspace",
        required=not any(arg in sys.argv for arg in ["-l", "--list", "-v", "--version"]),
        help="Path to workspace directory that contains test run files",
    )

    parser.add_argument(
        "-v",
        "--version",
        help="Display current version of ctam",
        action="store_true",
    )
    return parser.parse_args()

def get_exception_details(exec: Exception = ""):
    """
    :Description:                           It will trace back the exception object for getting
                                            mode details from the exception

    :param Exception exec:		            Exception object

    :returns:                               A dict object for all exception details
    :rtype:                                 Dict
    """
    exc_type, exc_obj, exc_tb = sys.exc_info()
    temp = exc_tb

    traceback_details = {}
    while temp:
        f_name = os.path.split(temp.tb_frame.f_code.co_filename)[1]
        traceback_details.update(
            {
                f_name: {
                    "filename": temp.tb_frame.f_code.co_filename,
                    "lineno": temp.tb_lineno,
                    "name": temp.tb_frame.f_code.co_name,
                }
            }
        )
        temp = temp.tb_next
    traceback_details.update(
        {
            "type": exc_type.__name__,
            "message": str(exec),  # or see traceback._some_str()
        }
    )
    return traceback_details


def main():
    args = parse_args()
    try:
        # builds hierarchy of test groups and associated test cases
        #ms_internal_tests

        if args.version:
            print(f"CTAM - version {__version__}")
            exit()
        
        dt = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        test_dir = "CTAM_LOGS"+"_{}".format(dt)
        if args.workspace:
            logs_output_dir = os.path.join(args.workspace, "TestRuns", test_dir)
            print("Output Dir is : ", logs_output_dir)
        else:        
            logs_output_dir = os.path.join("..{}workspace".format(os.sep), "TestRuns", test_dir)

        if not os.path.exists(logs_output_dir):
            os.makedirs(logs_output_dir)
        # When there are multiple output sources (like stdout, stderr, or logging) which can often conflict
        # with the progressbar, this will cause it to break onto the new lines or display inconsistently.
        # Hence wrap_Stderr() is used.
        progressbar.streams.wrap_stderr()
        raw_log_file = os.path.join(logs_output_dir, "Command_Line_Logs.log")
        redirect_output = RedirectOutput(raw_log_file)
        redirect_output.start()
        default_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "json_spec", "input")
        default_config_path = default_config_path.replace('/tmp/', '') if default_config_path.startswith('/tmp/') else default_config_path 
        if not args.workspace:
            ifc_dir = os.path.join(os.path.dirname(__file__), "interfaces")
            ext_test_root_dir =  os.path.join(os.path.dirname(__file__), "tests")
            test_hierarchy = TestHierarchy(ext_test_root_dir, ifc_dir)
            if args.list:
                test_hierarchy.print_test_groups_test_cases(args.group)
                return 0, None, "List of tests is printed"
            print("Invalid workspace specified")
            return 1, None, "Invalid workspace specified"

        required_workspace_files = [
            "dut_info.json",
            "redfish_uri_config.json",
            "test_runner.json",
            ".netrc",
        ]

        missing_files = [
            file_name for file_name in required_workspace_files if not os.path.isfile(os.path.join(args.workspace, file_name))
        ]
        if missing_files:
            for file_name in missing_files:
                print(f"The required file {file_name} does not exist in the workspace.")
            return 1, None, "Missing required files"
        print(f"Version : {__version__}")
        print(f"WorkSpace : {args.workspace}")
        
        
        # NOTE: Added to read default config file is its not present in workspace directory.
        # NOTE: Only .netrc and dut_info is required to run anything other than listing all the test cases.
        
        test_runner_json = os.path.join(args.workspace, "test_runner.json")
        if not os.path.isfile(test_runner_json):
            print("\033[91mUNABLE TO FIND test_runner.json IN WORKSPACE DIRECTORY.\nUSING THE test_runner.json FROM json_spec/input !!!\033[0m")
            test_runner_json = os.path.join(default_config_path, "test_runner.json")
        
        dut_info_json = os.path.join(args.workspace, "dut_info.json")
        
        package_info_json = os.path.join(args.workspace, "package_info.json")
        if not os.path.isfile(package_info_json):
            print("Package_info.json only needed for FW Test cases.")
            print("\033[91mUNABLE TO FIND package_info.json IN WORKSPACE DIRECTORY.\nUSING THE package_info.json FROM json_spec/input !!!\033[0m")
            package_info_json = os.path.join(default_config_path, "package_info.json")
        
        redfish_uri_config = os.path.join(args.workspace, "redfish_uri_config.json")
        if not os.path.isfile(redfish_uri_config):
            print("\033[91mUNABLE TO FIND redfish_uri_config.json IN WORKSPACE DIRECTORY.\nUSING THE redfish_uri_config.json FROM json_spec/input !!!\033[0m")
            redfish_uri_config = os.path.join(default_config_path, "redfish_uri_config.json")
        
        redfish_response_messages = os.path.join(args.workspace, "redfish_response_messages.json")
        if not os.path.isfile(redfish_response_messages):
            print("\033[91mUNABLE TO FIND redfish_response_messages.json IN WORKSPACE DIRECTORY.\nUSING THE redfish_response_messages.json FROM json_spec/input !!!\033[0m")
            redfish_response_messages = os.path.join(default_config_path, "redfish_response_messages.json")
        
        net_rc = os.path.join(args.workspace, ".netrc")
        
        # NOTE: We have added internal test directory as mandatory if 'internal_testing' is true in test runner json.
        # NOTE: If internal_test is true in test runner json then both internal and external tests we can run, else we can continue our existing flow.
        with open(test_runner_json, "r") as f:
            test_runner_config = json.load(f)

        internal_testing = test_runner_config.get("internal_testing", False)

        test_ifc_root_dir = test_runner_config.get("test_ifc_override_dir", os.path.dirname(__file__))

        ifc_dir = os.path.join(test_ifc_root_dir, "interfaces")
        ext_test_root_dir =  os.path.join(test_ifc_root_dir, "tests")

        if internal_testing:
            int_test_root_dir =  os.path.join(test_ifc_root_dir, "internal_tests")
            test_root_dir =  [ext_test_root_dir, int_test_root_dir]
            test_hierarchy = TestHierarchy(test_root_dir, ifc_dir)
        else:
            test_hierarchy = TestHierarchy(ext_test_root_dir, ifc_dir)

        if args.list:
            test_hierarchy.print_test_groups_test_cases(args.group)
            return 0, None, "List of tests is printed"

        if args.Discovery:
            runner = TestRunner(
                workspace_dir=args.workspace,
                logs_output_dir=logs_output_dir,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                redfish_response_messages=redfish_response_messages,
                net_rc=net_rc,
            )
            status_code, exit_string = runner.get_system_details()
            return status_code, None, exit_string

        elif args.testcase:
            runner = TestRunner(
                workspace_dir=args.workspace,
                logs_output_dir=logs_output_dir,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                redfish_response_messages=redfish_response_messages,
                net_rc=net_rc,
                single_test_override=args.testcase,
            )
        elif args.testcase_sequence:
            runner = TestRunner(
                workspace_dir=args.workspace,
                logs_output_dir=logs_output_dir,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                redfish_response_messages=redfish_response_messages,
                net_rc=net_rc,
                sequence_test_override=args.testcase_sequence,
            )
        elif args.group:
            runner = TestRunner(
                workspace_dir=args.workspace,
                logs_output_dir=logs_output_dir,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                redfish_response_messages=redfish_response_messages,
                net_rc=net_rc,
                single_group_override=args.group,
            )
        elif args.group_sequence:
            runner = TestRunner(
                workspace_dir=args.workspace,
                logs_output_dir=logs_output_dir,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                redfish_response_messages=redfish_response_messages,
                net_rc=net_rc,
                sequence_group_override=args.group_sequence,
            )
        else:
            all_tests = test_hierarchy.get_all_tests()
            runner = TestRunner(
                workspace_dir=args.workspace,
                logs_output_dir=logs_output_dir,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                net_rc=net_rc,
                redfish_uri_config_file=redfish_uri_config,
                redfish_response_messages=redfish_response_messages,
                run_all_tests=all_tests
            )

        status_code, exit_string = runner.run()
        log_directory = os.path.relpath(runner.output_dir, os.getcwd())
        return   status_code, log_directory, exit_string

    except (Exception, NotImplementedError) as e:
        exception_details = get_exception_details(e)
        print(f"Test Run Failed: {json.dumps(exception_details, indent=4)}")
        return 1, None, f"Test failed due to exception: {e}"


if __name__ == "__main__":
    status_code, log_directory, exit_string = main()
    print("\nTest exited with status code*: {} - {}".format("FAIL" if status_code else "PASS", exit_string))
    print(f"Log Directory: {log_directory}")
    print("\n*Note: Return/Status Codes - PASS(0): All tests passed, FAIL(1): Execution/runtime failure or test failure\n")
    exit(status_code)

