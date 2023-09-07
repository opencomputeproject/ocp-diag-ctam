"""
Copyright (c) Microsoft Corporation
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Collect Crashdump Manager
:Test ID:		R2
:Group Name:	ras
:Score Weight:	10

:Description:	Placeholder only. Post CollectDiagnisticData for '\redfish\v1\Managers\{Manager}\LogService\EventLog with DiagnosticDataType = Manager

:Usage 1:		python ctam.py -w ..\workspace -t R2
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Collect Crashdump Manager"

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
from tests.ras.basic_ras_test_group import (
    BasicRasTestGroup,
)


class CTAMTestCollectCrashdumpManager(TestCase):
    """
    Post CollectDiagnisticData for '\redfish\v1\Managers\{Manager}\LogService\EventLog with DiagnosticDataType = Manager

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Collect Crashdump Manager"
    test_id: str = "R2"
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
            if self.group.ras_ifc.ctam_discover_crashdump_cap() == []:
                step1.add_log(
                    LogSeverity.FATAL,
                    f"{self.test_id} : Test case Failed.",
                )
                result = False
            else:
                step1.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : Test case Passed.",
                )
                result = True

        if result:
            step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")
            with step2.scope():
                if self.group.ras_ifc.ctam_collect_crashdump_manager_list() == []:
                    step2.add_log(LogSeverity.FATAL, f"{self.test_id} : Test case Failed.")
                    result = False
                else:
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : Test case Passed.")
                    result = True

        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")
            with step3.scope():
                if self.group.ras_ifc.ctam_collect_crashdump_manager_list():
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : Test case Passed.")
                    result = True
                else:
                    step2.add_log(LogSeverity.FATAL, f"{self.test_id} : Test case Failed.")
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")
            with step4.scope():
                if self.group.ras_ifc.ctam_download_crashdump_attachment():
                    step2.add_log(LogSeverity.INFO, f"{self.test_id} : Test case Passed.")
                    result = True
                else:
                    step2.add_log(LogSeverity.FATAL, f"{self.test_id} : Test case Failed.")
                    result = False

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
