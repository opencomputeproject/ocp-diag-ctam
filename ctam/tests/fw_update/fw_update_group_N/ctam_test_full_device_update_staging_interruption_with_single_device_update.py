"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Full Device Update Staging Interruption With Single Device Update
:Test ID:		F24
:Group Name:	fw_update
:Score Weight:	10

:Description:	Test case of full firmware update in a loop. To verify the ongoing rollback is not affected by 
:Usage 1:		python ctam.py -w ..\workspace -t F24
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Full Device Update Staging Interruption With Single Device Update"

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


class CTAMTestFullDeviceUpdateInterruptionWithSingleDeviceUpdate(TestCase):
    """
    Verify single device fails whhen a full device fw update staging is in progress

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Full Device Update Staging Interruption With Single Device Update"
    test_id: str = "F24"
    score_weight: int = 10
    tags: List[str] = []

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
        fwupd_task_id = None

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            if not self.group.fw_update_ifc.ctam_fw_update_precheck(image_type="backup"):
                step1.add_log(LogSeverity.INFO, f"[{self.test_id}] : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )

        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
        with step2.scope():
            fwupd_status, fwupd_task_id = self.group.fw_update_ifc.ctam_stage_fw(image_type="backup", 
                                                                                 wait_for_stage_completion=False,
                                                                                 return_task_id=True)
            if fwupd_status:
                step2.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged")
            else:
                step2.add_log(
                    LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed"
                )
                result = False

        if result:
            step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3")  # type: ignore
            with step3.scope():
                if component_list := self.group.fw_update_ifc.ctam_build_updatable_device_list():
                    device = component_list[0]
                    step1_device = self.test_run().add_step(f"{self.__class__.__name__} run(), step1_{device}")  # type: ignore
                    with step1_device.scope():
                        if self.group.fw_update_ifc.ctam_selectpartiallist(count=1, specific_targets=[device]):
                            step1_device.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
                        else:
                            step1_device.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                            result = False

                    if result:
                        step2_device = self.test_run().add_step(f"{self.__class__.__name__} run(), step2_{device}")  # type: ignore
                        with step2_device.scope():
                            if self.group.fw_update_ifc.ctam_stage_fw(partial=1):
                                step2_device.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Staged - Unexpected")
                                result = False
                            else:
                                step2_device.add_log(
                                    LogSeverity.ERROR, f"{self.test_id} : FW Update Stage Failed as expected"
                                )
                else:
                    step3.add_log(LogSeverity.INFO, f"{self.test_id} : No updatable devices, exiting")
                    result = False

        if result:
            step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4")  # type: ignore
            with step4.scope():
                if fwupd_task_id is not None:
                    TaskCompleted, _ =  self.group.fw_update_ifc.ctam_monitor_task(fwupd_task_id)
                    if TaskCompleted: 
                        step4.add_log(
                            LogSeverity.INFO, f"{self.test_id} : FW Update Staging Verification"
                        )
                    else:
                        step4.add_log(
                            LogSeverity.ERROR, f"{self.test_id} : FW Update Staging Verification - Task Failed"
                        )
                        result = False
                else:
                    step4.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Staging Verification - No task ID",
                    )
                    result = False
                    
        if result:
            step5 = self.test_run().add_step(f"{self.__class__.__name__} run(), step5")  # type: ignore
            with step5.scope():
                if self.group.fw_update_ifc.ctam_activate_ac():
                    step5.add_log(
                        LogSeverity.INFO, f"{self.test_id} : FW Update Activate"
                    )
                else:
                    step5.add_log(
                        LogSeverity.ERROR,
                        f"{self.test_id} : FW Update Activation Failed",
                    )
                    result = False

        if result:
            step6 = self.test_run().add_step(f"{self.__class__.__name__} run(), step6")
            with step6.scope():
                if self.group.fw_update_ifc.ctam_fw_update_verify(image_type="backup"):
                    step5.add_log(
                        LogSeverity.INFO,
                        f"{self.test_id} : Update Verification Completed",
                    )
                else:
                    step6.add_log(
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
        return self.result

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
