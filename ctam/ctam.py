# Copyright (c) Microsoft Corporation
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import argparse
import os
import sys
import traceback
import json

from pathlib import Path

# until the folder structure gets fixed to a more pip/setuptools oriented format
# we need to manually adjust the path so that running the main script's imports work
sys.path.append(str(Path(__file__).resolve().parent))

from test_hierarchy import TestHierarchy
from test_runner import TestRunner


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

    parser.add_argument(
        "-w",
        "--workspace",
        required="-l" not in sys.argv and "--list" not in sys.argv,
        help="Path to workspace directory that contains test run files",
    )

    parser.add_argument(
        "-l",
        "--list",
        help="List all test cases. If combined with -G then list all cases of the chosen group ",
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


        if not os.path.isdir(args.workspace):
            print("Invalid workspace specified")
            return 1, None, "Invalid workspace specified"
        required_workspace_files = [
            "dut_info.json",
            "redfish_uri_config.json",
            ".netrc",
        ]

        missing_files = [
            file for file in required_workspace_files if not os.path.isfile(os.path.join(args.workspace, file))
        ]

        if missing_files:
            for file_name in missing_files:
                print(f"The required file {file_name} does not exist in the workspace.")
            return 1, None, "Missing required files"
        print(f"WorkSpace : {args.workspace}")
        test_runner_json = os.path.join(args.workspace, "test_runner.json")
        dut_info_json = os.path.join(args.workspace, "dut_info.json")
        package_info_json = os.path.join(args.workspace, "package_info.json")
        redfish_uri_config = os.path.join(args.workspace, "redfish_uri_config.json")
        net_rc = os.path.join(args.workspace, ".netrc")

        # NOTE: We have added internal test directory as mandatory if 'internal_testing' is true in test runner json.
        # NOTE: If internal_test is true in test runner json then both internal and external tests we can run, else we can continue our existing flow.
        with open(test_runner_json, "r") as f:
            test_runner_config = json.load(f)

        internal_testing = test_runner_config.get("internal_testing", False)

        ifc_dir = os.path.join(os.path.dirname(__file__), "interfaces")
        ext_test_root_dir =  os.path.join(os.path.dirname(__file__), "tests")

        if internal_testing:
            int_test_root_dir =  os.path.join(os.path.dirname(__file__), "internal_tests")
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
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
            )
            runner.get_system_details()
            return 0, None, "System discovery is done" # FIXME: Status code can be returned from get_system_details

        elif args.testcase:
            runner = TestRunner(
                workspace_dir=args.workspace,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
                single_test_override=args.testcase,
            )
        elif args.testcase_sequence:
            runner = TestRunner(
                workspace_dir=args.workspace,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
                sequence_test_override=args.testcase_sequence,
            )
        elif args.group:
            runner = TestRunner(
                workspace_dir=args.workspace,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
                single_group_override=args.group,
            )
        elif args.group_sequence:
            runner = TestRunner(
                workspace_dir=args.workspace,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
                sequence_group_override=args.group_sequence,
            )
        else:
            all_tests = test_hierarchy.get_all_tests()
            runner = TestRunner(
                workspace_dir=args.workspace,
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                net_rc=net_rc,
                redfish_uri_config_file=redfish_uri_config,
                run_all_tests=all_tests
            )

        status_code, exit_string = runner.run()
        log_directory = os.path.relpath(runner.output_dir, os.getcwd())
        return status_code, log_directory, exit_string

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
