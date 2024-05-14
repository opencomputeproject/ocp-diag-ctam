"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Service Validator
:Test ID:		T0
:Group Name:	Telemetry
:Score Weight:	10

:Description:	It will validate all of the available URIs.

:Usage 1:		python ctam.py -w ..\workspace -t T0
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Service Validator"

"""
from typing import Optional, List
from tests.test_case import TestCase
import os
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.telemetry.basic_telemetry_group.basic_telemetry_group import (
    BasicTelemetryTestGroup,
)
from utils.ctam_utils import GitUtils

class CTAMTestServiceValidator(TestCase):
    """

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Service Validator"
    test_id: str = "T0"
    score_weight: int = 10
    tags: List[str] = []
    compliance_level: str = ""

    # exclude_tags: List[str] = ["NotCheck"]

    def __init__(self, group: BasicTelemetryTestGroup):
        """
        _summary_
        """
        super().__init__()
        self.group = group

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
        result = True
        git = GitUtils()
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        repo_path = "RedfishServiceValidator"
        with step1.scope():
            result = git.clone_repo(repo_url="https://github.com/DMTF/Redfish-Service-Validator.git",
                                  repo_path="RedfishServiceValidator")

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                file_name="RedfishServiceValidator"
                base_uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}",
                                                                    component_type="GPU")
                log_path = os.path.join(self.dut().logger_path, file_name)
                schema_directory = f".{os.sep}SchemaFiles"
                connection_url = self.dut().connection_url + base_uri
                result = git.validate_redfish_service(file_name=file_name, connection_url=connection_url,
                                                       user_name=self.dut().user_name, user_pass=self.dut().user_pass,
                                                       log_path=self.dut().logger_path, schema_directory=schema_directory,
                                                       depth="Tree",
                                                       service_uri="/redfish/v1")
                
        step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
        with step3.scope():
            git.clean_repo()
        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

        # call super last to log result and score
        super().run()
        return self.result

    def teardown(self):
        """
        undo environment state change from setup() above, this function is called even if run() fails or raises exception
        """
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            pass

        # call super teardown last
        super().teardown()
