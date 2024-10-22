"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Full Device Update Staging Interruption With AC Reset
:Test ID:		F24
:Group Name:	fw_update
:Score Weight:	10

:Description:	Before running this test case we expect to be on N image. We will do staging with N-1 image which is getting interrupted by ac
                power reset. At least one of the components should stay on N image after ac power reset.
:Usage 1:		python ctam.py -w ..\workspace -t F24
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update Staging Interruption With AC Reset"

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


class CTAMTestFullDeviceUpdateStagingInterruptionWithAcReset(TestCase):
    """
    Verify single device fails whhen a full device fw update staging is in progress

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Full Device Update Staging Interruption With AC Reset"
    test_id: str = "F24"
    score_weight: int = 10
    tags: List[str] = ["Negative", "L2", "Single_Device"]
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
        status_message = ""
        result = True
        fwupd_task_id = None

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            status, status_message = self.group.fw_update_ifc.ctam_fw_update_precheck(image_type="backup")
            if not status:
                step1.add_log(LogSeverity.INFO, f"[{self.test_id}] : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )
                status_message += " " + "FW Update Not Required"

        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
        with step2.scope():
            fwupd_status, status_msg, fwupd_task_id = self.group.fw_update_ifc.ctam_stage_fw(image_type="backup", 
                                                                                 wait_for_stage_completion=False)
            status_message += " " + status_msg
            if fwupd_status:
                step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
            else:
                step2.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                )
                status_message += " " + "FW Update Stage Failed"
                result = False
                    
        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_activate_ac()
                status_message += status_msg
                if status:
                    step3.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                    )
                else:
                    step3.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Activation Failed",
                    )
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")
            with step4.scope():
                status, status_msg = self.group.fw_update_ifc.ctam_fw_update_verify(version_check=False)
                status_message += " " + status_msg
                if status:
                    step4.add_log(
                        LogSeverity.INFO,
                        f"{self.test_id} : Update Verification Completed",
                    )
                else:
                    step4.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : Update Verification Failed",
                    )
                    result = False

        # ensure setting of self.result and self.score prior to calling super().run()
        self.result = TestResult.PASS if result else TestResult.FAIL
        if self.result == TestResult.PASS:
            self.score = self.score_weight

        # call super last to log result and score
        super().run()
        return self.result, status_message

    def teardown(self):
        """
        undo environment state change from setup() above, this function is called even if run() fails or raises exception
        """
        # add custom teardown here
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown()...")
        with step1.scope():
            if self.group.fw_update_ifc.ctam_pushtargets():
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Push URI Targets Reset")
            else:
                step1.add_log(LogSeverity.WARNING, f"{self.test_id} : Push URI Targets Reset - Failed")

        # call super teardown last
        super().teardown()
