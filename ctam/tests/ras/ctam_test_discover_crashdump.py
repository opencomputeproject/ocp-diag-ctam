"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Discover Crashdump
:Test ID:		R1
:Group Name:	ras
:Score Weight:	10

:Description:	Ensure that we have at least one LogServiceids each under Systems and Managers. 
                Next it checks to see if at least one of them have LogService.CollectDiagnosticData 
                Return list of uris with LogService.CollectDiagnosticData. For eg. this is a pass. 
                /redfish/v1/Managers/{ManagerId}/LogServices/{LogServiceId}/Actions/CollectDiagnosticData 
                /redfish/v1/Systems/{ComputerSystemId}/LogServices/{LogServiceId}/Actions/CollectDiagnosticData

:Usage 1:		python ctam.py -w ..\workspace -t R1
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Discover Crashdump"

"""
from typing import Optional, List
from tests.test_case import TestCase
from pprint import pprint
from ocptv.output import (
    DiagnosisType,
    LogSeverity,
    SoftwareType,
    TestResult,
    TestStatus,
)
from tests.ras.basic_ras_test_group import (
    BasicRasTestGroup,
)


class CTAMTestDiscoverCrashdump(TestCase):
    """
    Get CollectDiagnosticDataActionInfo & discover non empty Allowable Values for DiagnosticDataType, OEMDiagnosticDataType

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Discover Crashdump"
    test_id: str = "R1"
    score_weight: int = 10
    tags: List[str] = []

    # exclude_tags: List[str] = ["NotCheck"]

    def __init__(self, group: BasicRasTestGroup):
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
            if (collectdata:=self.group.ras_ifc.ctam_discover_crashdump_cap()) == []:
                step1.add_log(
                    LogSeverity.FATAL,
                    f"{self.test_id} : Test case Failed - CollectDiagnostic list is empty",
                )
                result = False
            else:
                print(collectdata)
                step1.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : Test case Passed.",
                )
                result = True

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
