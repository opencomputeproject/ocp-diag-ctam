# Copyright (c) Microsoft Corporation
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import argparse
import os
import sys
import traceback
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


def main():
    args = parse_args()

    try:
        # builds hierarchy of test groups and associated test cases
        test_hierarchy = TestHierarchy(os.path.join(os.getcwd(), "tests"), os.path.join(os.getcwd(), "interfaces"))

        if args.list:
            test_hierarchy.print_test_groups_test_cases(args.group)
            exit(0)

        if not os.path.isdir(args.workspace):
            print("Invalid workspace specified")
            exit(1)
        required_workspace_files = [
            "dut_info.json",
            "package_info.json",
            "test_runner.json",
            "redfish_uri_config.json",
            ".netrc",
        ]

        missing_files = [
            file for file in required_workspace_files if not os.path.isfile(os.path.join(args.workspace, file))
        ]

        if missing_files:
            for file_name in missing_files:
                print(f"The required file {file_name} does not exist in the workspace.")
            exit(1)
        print(f"WorkSpace : {args.workspace}")
        test_runner_json = os.path.join(args.workspace, "test_runner.json")
        dut_info_json = os.path.join(args.workspace, "dut_info.json")
        package_info_json = os.path.join(args.workspace, "package_info.json")
        redfish_uri_config = os.path.join(args.workspace, "redfish_uri_config.json")
        net_rc = os.path.join(args.workspace, ".netrc")
        if args.Discovery:
            runner = TestRunner(
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
            )
            runner.get_system_details()
            sys.exit(1)

        elif args.testcase:
            runner = TestRunner(
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
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                redfish_uri_config_file=redfish_uri_config,
                net_rc=net_rc,
                sequence_group_override=args.group_sequence,
            )
        else:
            runner = TestRunner(
                test_hierarchy=test_hierarchy,
                test_runner_json_file=test_runner_json,
                dut_info_json_file=dut_info_json,
                package_info_json_file=package_info_json,
                net_rc=net_rc,
                redfish_uri_config_file=redfish_uri_config,
            )

        runner.run()

    except (NotImplementedError, Exception) as e:
        exception_details = traceback.format_exc()
        print(f"Test Run Failed: {exception_details}")
        exit(1)


if __name__ == "__main__":
    main()
