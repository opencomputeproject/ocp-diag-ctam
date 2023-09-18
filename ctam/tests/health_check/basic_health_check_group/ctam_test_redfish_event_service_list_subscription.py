"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Redfish Event Service List Subscriptions
:Test ID:		H80
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test attempts to get event subscriptions

:Usage 1:		python ctam.py -w ..\workspace -t H80
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Redfish Event Service List Subscriptions"

"""
from typing import Optional, List
from tests.test_case import TestCase
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


class CTAMTestRedfishEventServiceSubscription(TestCase):
    """
    List all Event Service Subscription

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Redfish Event Service List Subscriptions"
    test_id: str = "H80"
    score_weight: int = 10
    tags: List[str] = ["HCheck"]

    # exclude_tags: List[str] = ["NotCheck"]

    def __init__(self, group: BasicHealthCheckTestGroup):
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
        
        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            JSONData = self.group.health_check_ifc.ctam_getes("Subscriptions")
            if JSONData is None or len(JSONData) == 0:
                step1.add_log(LogSeverity.ERROR, f"{self.test_id} : Redfish Event Service Subscriptions Check - Failed")
                result = False
            else:
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Redfish Event Service Subscriptions Check - Completed")
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : {JSONData}")

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
