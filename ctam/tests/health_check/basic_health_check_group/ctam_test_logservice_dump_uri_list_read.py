r"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test LogService Dump URI List Read
:Test ID:		H97
:Group Name:	health_check
:Score Weight:	10
:Spec Versions: ">= 1.0"

:Description:   This test verifies the ability to read the list of dump URIs from the LogService. It performs the following steps:

1. Retrieve the list of dump URIs from the LogService.
   Example URI: /redfish/v1/Systems/{BaseboardID}/LogServices/Dump
2. Check if the list of dump URIs is successfully retrieved.
3. If the list of dump URIs is not retrieved, log the failure and mark the test as failed.
4. If the list of dump URIs is successfully retrieved, mark the test as passed.

PASS Criteria:
- The list of dump URIs is successfully retrieved.

FAIL Criteria:
- The list of dump URIs is not successfully retrieved.


:Usage 1:		python ctam.py -w ..\workspace -t H97
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test LogService Dump URI List Read"

:Dependencies: None
                        
r"""
from typing import Optional, List, Union
from tests.test_case import TestCase
from pprint import pprint
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

class CTAMTestLogServiceDumpURIListRead(TestCase):
    r"""
        :param gpu_bb acc:		Accelerator Object
        :param Logger logger:	Logger Object

        :returns:				Test result [Pass/Fail], Test score
    r"""

    test_name: str = "CTAM Test LogService Dump URI List Read"
    test_id: str = "H97"
    score_weight: int = 10
    tags: List[str] = ["L3"]
    compliance_level: str = "L3"
    spec_versions: Union[str, List[str]] = ">= 1.0"

    def __init__(self, group: BasicHealthCheckTestGroup):
        r"""
        _summary_
        r"""
        super().__init__()
        self.group = group

    def setup(self):
        r"""
        set environment state for this test only
        r"""
        # call super first
        super().setup()

        # add custom setup here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  setup()...")
        with step1.scope():
            pass

    def run(self) -> TestResult:
        r"""
        actual test verification
        r"""
        failure_reason = ""
        result = True
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if (dump_uri := self.group.health_check_ifc.ctam_get_all_logdump_uris()) == []:
                step1.add_log(
                    LogSeverity.FATAL,
                    f"{self.test_id} : Redfish LogService Dump URI list Read Failed - Dump list is empty",
                )
                failure_reason += "Dump URI list read failed"
                result = False
            else:
                #pprint(dump_uri)
                step1.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : Redfish LogService Dump URI list Read Completed.",
                )
                
        
        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
            with step2.scope():
                if self.group.health_check_ifc.ctam_verify_logdump_presence():
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : Redfish LogService Dump URI list Verification - Passed")
                else:
                    step2.add_log(LogSeverity.ERROR,f"{self.test_id} : Redfish LogService Dump URI list Verification - Failed")
                    failure_reason = "Dump URI list verification failed"
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

        # call super last to log result and score
        super().run()
        return self.result, failure_reason

    def teardown(self):
        r"""
        undo environment state change from setup() above, this function is called even if run() fails or raises exception
        r"""
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            pass

        # call super teardown last
        super().teardown()
