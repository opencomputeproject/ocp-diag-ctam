"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Redfish Interop Validator Firmware Inventory
:Test ID:		H5
:Group Name:	health_check
:Score Weight:	10

:Description:	This test validates the Firmware Inventory using RIV

:Usage 1:		python ctam.py -w ..\workspace -t H5
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Redfish Interop Validator Firmware Inventory"

"""
from typing import Optional, List
from tests.test_case import TestCase
from test_hierarchy import TestHierarchy
import os
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.health_check.basic_health_check_group.basic_health_check_test_group import (
    BasicHealthCheckTestGroup,
)
from utils.ctam_utils import GitUtils

class CTAMTestRedfishInteropValidatorFirmwareInventory(TestCase):
    """
    Verify values of Firmware Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Redfish Interop Validator Firmware Inventory"
    test_id: str = "H5"
    score_weight: int = 10
    tags: List[str] = ["HCheck", "L1"]
    compliance_level: str ="L1"

    # exclude_tags: List[str] = ["NotCheck"]

    def __init__(self, group: BasicHealthCheckTestGroup):
        """
        _summary_
        """
        super().__init__()
        self.group = group
        self.git_utils = GitUtils()

    def setup(self):
        """
        set environment state for this test only
        """
        # call super first
        super().setup()

        # add custom setup here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  setup()...")
        with step1.scope():
            pass

    def run(self) -> TestResult:
        """
        actual test verification
        """
        status_msg = ""
        result = True
        logger_path = os.path.join(self.dut().logger_path, "RedfishInteropValidator", f"{self.__class__.test_id}_{self.__class__.__name__}")

        #cloning Redfish Interop Validator under temp folder which will be deleted after completion of test case.
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            result = self.git_utils.clone_repo(repo_url="https://github.com/microsoft/Redfish-Interop-Validator.git",
                                  repo_path="Redfish-Interop-Validator")

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                # Change this JSON file name and path if you want to run any other excel.
                source_json = "FirmwareInventory.json"
                json_file_path = os.path.join(self.dut().default_config_path, source_json)
                #Running RedfishInteropValidator using json profiles.
                file_name="RedfishInteropValidator"
                base_uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}",
                                                                    component_type="GPU")
                repo_file_name = os.path.join(self.git_utils.repo_path, file_name)
                
                result, _ = GitUtils.ctam_redfish_interop_validator(file_name=repo_file_name, connection_url=self.dut().connection_url,
                                                user_name=self.dut().user_name, user_pass=self.dut().user_pass,
                                                log_path=logger_path, passthrough=base_uri,
                                                payload="NodeTree /redfish/v1/UpdateService/FirmwareInventory",
                                                profile=json_file_path,
                                                )
                if not result:
                    step2.add_log(LogSeverity.ERROR, f"Something went wrong while running redfish command.")
                step2.add_log(LogSeverity.INFO, f"Redfish Service Command ran successfully and validated.")

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

        # call super last to log result and score
        super().run()
        return self.result, status_msg

    def teardown(self):
        """
        undo environment state change from setup() above, this function is called even if run() fails or raises exception
        """
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            step1.add_log(LogSeverity.INFO, f"Cleaning repo after running Redfish Interop Validator.")
            self.git_utils.clean_repo()

        # call super teardown last
        super().teardown()
