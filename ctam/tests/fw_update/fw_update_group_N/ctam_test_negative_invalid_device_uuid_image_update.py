"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Invalid Device UUID Image Update
:Test ID:		F28
:Group Name:	fw_update
:Score Weight:	10

:Description:	This test case is a Negative Test. It'll make a copy of the default FW image provided in package_info.json 
                and corrput the UUID in all FirmwareDeviceIDRecords. Then it'll attempt firmware update with the fwpkg containing corrupted device UUIDs. 

:Usage 1:		python ctam.py -w ..\workspace -t F28
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Negative Invalid Device UUID Image Update"

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
from tests.fw_update.fw_update_group_N._fw_update_group_N import (
    FWUpdateTestGroupN,
)


class CTAMTestNegativeInvalidDeviceUUIDImageUpdate(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Invalid Device UUID Image Update"
    test_id: str = "F28"
    score_weight: int = 10
    tags: List[str] = ["Negative", "L2"]
    compliance_level: str = "L2"

    def __init__(self, group: FWUpdateTestGroupN):
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
            status, status_msg, task_id = self.group.fw_update_ifc.ctam_stage_fw(partial=1, 
                                                                                 image_type="invalid_device_uuid")
            if status:
                step1.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : FW Update Stage Initiation Failed as Expected",
                )
            else:
                step1.add_log(
                    LogSeverity.ERROR,
                    f"{self.test_id} : FW Update Staging Initiated - Unexpected",
                )
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
            if self.group.fw_update_ifc.ctam_activate_ac(gpu_check=False, fwupd_hyst_wait=False):
                msg = f"{self.test_id} : AC Cycle Passed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)  
            else:
                msg = f"{self.test_id} : AC Cycle Failed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)

        # call super teardown last
        super().teardown()
