"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Service Validator
:Test ID:		T0
:Group Name:	Telemetry
:Score Weight:	10
:Spec Versions:  ">= 1.0"   

:Description:	This testcase will clone the RedfishServiceValidator repository and It will validate all of the available URIs under redfish.

                :PASS Criteria: 
                The test will pass if the Redfish Service Validator command runs successfully and validates
                the Redfish service without errors.

                :FAIL Criteria: 
                The test will fail if there is an error in cloning the repository, running the Redfish Service
                Validator command, or if the validation finds issues with the Redfish service on the DUT.

:Usage 1:		python ctam.py -w ..\workspace -t T0
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Service Validator"


:Dependencies: None

"""
from typing import Optional, List, Union
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

    test_name: str = "CTAM Test Redfish Service Validator"
    test_id: str = "T0"
    score_weight: int = 10
    tags: List[str] = ["L2"]
    compliance_level: str = "L2"
    spec_versions: Union[str, List[str]] = ">= 1.0"

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
        failure_reason = ""
        result = True
        git = GitUtils()
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        repo_path = "RedfishServiceValidator"
        
        with step1.scope():
            step1.add_log(LogSeverity.INFO, f"Cloning repo for Redfish Service Validator.")
            result = git.clone_repo(repo_url="https://github.com/DMTF/Redfish-Service-Validator.git",
                                  repo_path="RedfishServiceValidator")
            if not result:
                step1.add_log(LogSeverity.ERROR, f"Cloning repo for Redfish Service Validator failed.")
                failure_reason += "Cloning repo failed. "
            step1.add_log(LogSeverity.INFO, f"Cloning repo for Redfish Service Validator successful.")
        
        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                file_name="RedfishServiceValidator"
                base_uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}",
                                                                    component_type="GPU")
                log_path = os.path.join(self.dut().logger_path, file_name)
                schema_directory = f".{os.sep}SchemaFiles"
                connection_url = self.dut().connection_url + base_uri
                
                step2.add_log(LogSeverity.INFO, f"Running Redfish Service command.")
                result, msg = git.validate_redfish_service(file_name=file_name, connection_url=connection_url,
                                                       user_name=self.dut().user_name, user_pass=self.dut().user_pass,
                                                       log_path=self.dut().logger_path, schema_directory=schema_directory,
                                                       depth="Single",
                                                       service_uri="/redfish/v1")
                if not result:
                    step2.add_log(LogSeverity.ERROR, f"Something went wrong while running redfish command. Please see error msg {msg}.")
                    failure_reason += "Error occurred running Redfish command."
                step2.add_log(LogSeverity.INFO, f"Redfish Service Command ran successfully and validated.")
        
        step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
        with step3.scope():
            step3.add_log(LogSeverity.INFO, f"Cleaning repo after Redfish Service Validated.")
            git.clean_repo()
        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

        # call super last to log result and score
        super().run()
        return self.result, failure_reason

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
