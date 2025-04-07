"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Test Name:		CTAM Test Negative Empty Metadata Image Update
:Test ID:		F26
:Group Name:	fw_update
:Score Weight:	10

:Description:	
    This test case is a negative test. It makes a copy of the default FW image provided in package_info.json
    and clears the metadata of any component in the PLDM bundle. Then it attempts a firmware update with the fwpkg containing corrupted UUID. 
    The objective is to ensure that the system correctly handles the corrupted metadata and does not proceed with the update.

:PASS Criteria:	
    - The firmware staging operation fails as expected due to the corrupted metadata.

:FAIL Criteria:	
    - The firmware staging operation succeeds unexpectedly with the corrupted metadata.

:Usage 1:		python ctam.py -w ..\workspace -t F26
:Usage 2:		python ctam.py -w ..\workspace -t "CTAM Test Negative Empty Metadata Image Update"

:Dependencies: 

<redfish_uri_config.json> : Required - <UpdateURI>, <TaskServiceURI>, <GPUCheckURI>, <MultiPartPushUriSupport>
                            Optional - <exclude_targets_list>, <HttpPushUriTargets>, <MultiPartFormData>, <IsMultiPart>
                            
<dut_info.json>           : Required - <FwActivationTimeMax>, <FwStagingTimeMax>, <PowerOffWaitTime>, <PowerOnWaitTime>, <IdleWaitTimeAfterFirmwareUpdate>, <PowerOffCommand>, <PowerOnCommand>
                            Optional - <SingleShotPowerCycle>, <SingleShotPowerCycleCommand>
                            
<package_info.json>       : Required - <Path>, <Package>, <JSON>, <CorruptComponentIdentifier>
                            Optional - <HasSignature>, <SignatureStructBytes>, <MetadataSizeBytes>
                                                      
<redfish_response_messages.json> : Required - <UpdateProgress_Message>
                                   Optional -  <LargeFWImageUpdate>
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


class CTAMTestNegativeEmptyMetadataImageUpdate(TestCase):
    """
    Verify values of Software Inventory Collection are present

    :param TestCase: super class for all test cases
    :type TestCase:
    """

    test_name: str = "CTAM Test Negative Empty Metadata Image Update"
    test_id: str = "F26"
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
        result = True
        failure_reason = ""

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")  # type: ignore
        with step1.scope():
            status, failure_reason = self.group.fw_update_ifc.ctam_fw_update_precheck()
            if not status:
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : FW Update Capable")
            else:
                step1.add_log(
                    LogSeverity.INFO, f"{self.test_id} : FW Update Not Required"
                )
        
        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")  # type: ignore
        with step2.scope():
            corrupted_component_id  = self.group.fw_update_ifc.ctam_get_component_to_be_corrupted(VendorProvidedBundle=False)
            corrupted_component_list = self.group.fw_update_ifc.ctam_get_component_list(component_id=corrupted_component_id)
            step2.add_log(LogSeverity.INFO, f"{self.test_id} : Selected component to corrupt -> ID: {corrupted_component_id} List: {corrupted_component_list}")
        
        step3 = self.test_run().add_step(f"{self.__class__.__name__} run(), step3_{corrupted_component_list[0]}")  # type: ignore
        with step3.scope():
            if self.group.fw_update_ifc.ctam_selectpartiallist(count=1, specific_targets=[corrupted_component_list[0]]):
                step3.add_log(LogSeverity.INFO, f"{self.test_id} : Single Device Selected")
            else:
                step3.add_log(LogSeverity.ERROR, f"{self.test_id} : Single Device Selection Failed")
                failure_reason += f"{self.test_id} : Single Device Selection Failed"
                result = False

        step4 = self.test_run().add_step(f"{self.__class__.__name__} run(), step4_{corrupted_component_list[0]}")  # type: ignore
        with step4.scope():
            status, status_msg, task_id = self.group.fw_update_ifc.ctam_stage_fw(partial=1, image_type="empty_metadata", 
                                                                                 corrupted_component_id=corrupted_component_id,
                                                                                 specific_targets=[corrupted_component_list[0]])
            failure_reason += " " + status_msg
            if status:
                step4.add_log(
                    LogSeverity.INFO,
                    f"{self.test_id} : FW Update Stage Initiation Failed as Expected",
                )
            else:
                step4.add_log(
                    LogSeverity.ERROR,
                    f"{self.test_id} : FW Update Staging Initiated - Unexpected",
                )
                failure_reason += " " + "FW Update Staging Initiated - Unexpected"
                result = False

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
        step1 = self.test_run().add_step(f"{self.__class__.__name__}  teardown(), Step1")
        with step1.scope():
            if self.group.fw_update_ifc.ctam_pushtargets():
                step1.add_log(LogSeverity.INFO, f"{self.test_id} : Push URI Targets Reset")
            else:
                step1.add_log(LogSeverity.WARNING, f"{self.test_id} : Push URI Targets Reset - Failed")
            
        step2 = self.test_run().add_step(f"{self.__class__.__name__} run(), step2")
        with step2.scope():
            if self.group.fw_update_ifc.ctam_activate_ac(gpu_check=False, fwupd_hyst_wait=False):
                msg = f"{self.test_id} : Teardown : AC Cycle Passed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)  
            else:
                msg = f"{self.test_id} : Teardown : AC Cycle Failed"
                self.test_run().add_log(LogSeverity.DEBUG, msg)
        
        # call super teardown last
        super().teardown()
