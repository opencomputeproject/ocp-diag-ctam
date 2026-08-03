"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
import ast
import os
import json
import time
import random
from interfaces.functional_ifc import FunctionalIfc
from ocptv.output import LogSeverity
from utils.fwpkg_utils import PLDMUnpack
from utils.json_utils import *

try:
    from internal_interfaces.fw_update_ifc_int import FwUpdateIfcInt as Meta
except:
    from utils.ctam_utils import MetaNull as Meta


class FWUpdateIfc(FunctionalIfc, metaclass=Meta):
    """
    API's related to general health check of the dut
    """

    # _instance: Optional["FWUpdateIfc"] = None

    # def __new__(cls, *args, **kwargs):
    #     """
    #     ensure only 1 instance can be created

    #     :return: instance
    #     :rtype: FWUpdateIfc
    #     """
    #     if not isinstance(cls._instance, cls):
    #         cls._instance = super(FWUpdateIfc, cls).__new__(cls, *args, **kwargs)
    #     return cls._instance
    
    def __init__(self):
        super().__init__()
        self.included_targets = []
        self.PostInstallVersionDetails = {}
        self.PreInstallVersionDetails = {}
        self._PLDMComponentVersions = {} # { image_type: {SoftwareID: ComponentVersionString}}
        self.NegativeTestImages = ["invalid_sign", "unsigned_component_image", "corrupt", \
                                    "invalid_pkg_uuid", "invalid_device_uuid", "empty_metadata", \
                                    "corrupt_component", "unsigned_bundle"]

    # @classmethod
    # def get_instance(cls, *args, **kwargs):
    #     """
    #     if there is an existing instance, return it, otherwise create the singleton instance and return it

    #     :return: instance
    #     :rtype: FWUpdateIfc
    #     """
    #     if not isinstance(cls._instance, cls):
    #         cls._instance = cls(*args, **kwargs)
    #     return cls._instance

    def PLDMComponentVersions(self, image_type):
        """
        :Description:       if the FW versions from PLDM bundle file are already populated, just return the existing dictionary.
                            Other

        :param image_type:  image_type

        :return:            _PLDMComponentVersions
        :rtype:             dict
        """
        if not self._PLDMComponentVersions.get(image_type):
            self.test_run().add_log(severity=LogSeverity.INFO, message=f"Populating FW Versions for image_type = {image_type}")
            self._PLDMComponentVersions[image_type] = self.ctam_get_version_from_bundle(image_type)
        return self._PLDMComponentVersions[image_type]

    def ctam_get_fw_version(self, PostInstall=0):
        """
        :Description:               Get Firmware Version
        :param PostInstall:     Get Version after install the Firmware or before installing

        :returns:                   None
        """

        MyName = __name__ + "." + self.ctam_get_fw_version.__qualname__
        JSONData = self.ctam_getfi(expanded=1)
        if PostInstall:
            self.PostInstallDetails = JSONData["Members"]
            jsonmultihunt(
                self.PostInstallDetails, "Id", "Version", self.PostInstallVersionDetails
            )
        else:
            self.PreInstallDetails = JSONData["Members"]
            jsonmultihunt(
                self.PreInstallDetails, "Id", "Version", self.PreInstallVersionDetails
            )
        msg = f"Post install version details are {self.PostInstallVersionDetails} and Pre install details are {self.PreInstallVersionDetails}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)

    def ctam_fw_update_precheck(self, image_type="default"):
        """
        :Description:               Check Firmware before installation
        :param image_type:          Type of the Firmware image

        :returns:                   VersionsDifferent
        :rtype:                     Bool
        """
        MyName = __name__ + "." + self.ctam_fw_update_precheck.__qualname__
        VersionsDifferent = True
        failure_reason = ""
        # if all component is update not needed then return update not needed. If any one component is updatable return updatable
        self.ctam_get_fw_version(PostInstall=0)

        # Getting all Component Ids with Version from PLDM Bundle JSON file
        BundleComponentIdsAndVersions = self.PLDMComponentVersions(image_type=image_type)
        for element in self.PreInstallDetails:
        #     # Check ONLY the ones which are part of HttpPushURITargets
            try:
                if (
                    self.included_targets == []
                    or element["@odata.id"] in self.included_targets
                ):
                    _excl = self.dut().redfish_uri_config.get("GPU_FWUpdate", {}).get("exclude_targets_list", [])
                    if any(element["Id"] == e or element["Id"].startswith(e) for e in _excl):
                            msg = f"Skipping {element['Id']} as it is in the exclude list"
                            self.test_run().add_log(LogSeverity.DEBUG, msg)
                            continue
                    msg = f"Pre Install Details: {element['Id']} : {element.get('SoftwareId', None)} : {element.get('Version', 'NA')} : "
                    if str(element["Updateable"]) == "True":

                        SoftwareId = str(hex(int(element["SoftwareId"], 16)))
                        if SoftwareId in BundleComponentIdsAndVersions.keys():

                            Package_Version = self.PLDMComponentVersions(image_type=image_type).get(SoftwareId)
                            if not Package_Version:
                                msg += "Not in the PLDM bundle"

                            elif element["Version"] not in Package_Version and (
                                self.included_targets == []
                                or element["@odata.id"] in self.included_targets
                            ):
                                VersionsDifferent = False
                                msg += f"Update Capable to {Package_Version}"

                            else:
                                msg += "Update Not Needed ."
                        else:
                            msg += "SoftwareId not found in PLDM JSON."
                        self.test_run().add_log(LogSeverity.DEBUG, msg)
                    else:
                        # Not in HttpPushURITargets
                        pass
            except Exception as e:
                failure_reason += " Exception occured: " + str(e)
                self.test_run().add_log(LogSeverity.ERROR, "Exception occured: " + str(e))
                VersionsDifferent = False

        return VersionsDifferent, failure_reason
    
    def ctam_stage_time_check(self, stage_time):
        FwStagingTimeMax = self.dut().dut_config["FwStagingTimeMax"]["value"]
        if stage_time > FwStagingTimeMax:
            stage_msg = f"staging time = {stage_time} seconds, Expected <= {FwStagingTimeMax} seconds."
            self.test_run().add_log(LogSeverity.DEBUG, stage_msg)
            status = False
        else:
            status = True
            stage_msg = ""
        return status, stage_msg
            
    def ctam_stage_fw(
        self, partial=0, image_type="default", wait_for_stage_completion=True,
        corrupted_component_id=None, corrupted_component_list=[],
        check_time=False, specific_targets=[], is_force_update=True
    ):
        """
        :Description:                           Stage Firmware
        :param partial:                         Partial
        :param image_type:                      Type of Firmware Image
        :param wait_for_stage_completion:       Wait for stage completion
        :param corrupted_component_id:          ComponentIdentifier of the component image to be corrupted for specific negative tests
        :param corrupted_component_list:        List component names (Ids) which are corrupted
        :param check_time:                      Check the staging time does not exceed maximum time per spec

        :returns:                               StageFWOOB_Status, StageFWOOB_Status_message, return_task_id 
        :rtype:                                 Bool, str, str
        """
        failure_reason = ""
        MyName = __name__ + "." + self.ctam_stage_fw.__qualname__
        StartTime = time.time()
        pushtargets = self.dut().uri_builder.format_uri(redfish_str="{HttpPushUriTargets}", component_type="GPU_FWUpdate")
        staging_time = 0
        if partial == 0 and pushtargets:
            self.ctam_pushtargets()
        JSONFWFilePayload = self.get_JSONFWFilePayload_file(image_type=image_type, corrupted_component_id=corrupted_component_id)
        if not JSONFWFilePayload or not os.path.isfile(JSONFWFilePayload):
            self.test_run().add_log(LogSeverity.DEBUG, f"Package file not found at path {JSONFWFilePayload}!!!")
            if corrupted_component_id != None:
                failure_reason = "Error in creating corrupted component!"
            else:
                failure_reason = "Package file missing in workspace!"
            return False, failure_reason, "", staging_time
        if self.dut().is_debug_mode():
            print(JSONFWFilePayload)
        update_uri = self.dut().redfish_uri_config.get("GPU_FWUpdate", {}).get("UpdateURI", "")
        if update_uri:
            base_uri = self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}", component_type="GPU"
            )
            uri = base_uri + update_uri
            status = True
            is_multipart = self.dut().redfish_uri_config.get("GPU_FWUpdate", {}).get("IsMultiPart", False)
        else:
            status, uri, is_multipart = self.get_update_uri()
            uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}" + uri, component_type="GPU")
        if not status:
            self.test_run().add_log(LogSeverity.DEBUG, f"Unable to find update uri from UpdateService resource!!!")
            failure_reason = "Update URI missing from UpdateService!"
            return False, failure_reason, "", staging_time
        if not specific_targets:
            cfg_targets = self.dut().redfish_uri_config.get("GPU_FWUpdate", {}).get("specific_targets", [])
            if isinstance(cfg_targets, str):
                cfg_targets = ast.literal_eval(cfg_targets) if cfg_targets else []
            specific_targets = [t for t in (cfg_targets or []) if t]
        targets = [t if str(t).startswith("/redfish/") else self.get_target_inventorys([t])[0]
                   for t in specific_targets]
        if self.dut().is_debug_mode():
            self.test_run().add_log(LogSeverity.DEBUG, f"URI : {uri}")
            self.test_run().add_log(LogSeverity.DEBUG, f"Targets : {targets}")
        # is_force_update = image_type == "backup" or image_type == "old_version"
        JSONData = self.RedFishFWUpdate(JSONFWFilePayload, uri, targets=targets, is_multipart=is_multipart, is_force_update=is_force_update)
        StagingStartTime = time.time()

        if self.dut().is_debug_mode():
            self.test_run().add_log(LogSeverity.DEBUG, f"{MyName}  {JSONData}")
        stage_msg = ""
        FwUpdTaskID = JSONData.get("Id")
        StageFWOOB_Status = False
        if "error" not in JSONData:
            if wait_for_stage_completion:
                if self.dut().is_debug_mode():
                    self.test_run().add_log(LogSeverity.DEBUG, FwUpdTaskID)
                DeployTime = time.time()
                FwStagingTimeMax = self.dut().dut_config["FwStagingTimeMax"]["value"]
                StageFWOOB_Status, JSONData = self.ctam_monitor_task(FwUpdTaskID)
                EndTime = time.time()
                staging_time = EndTime - StagingStartTime
                if check_time and (EndTime - StagingStartTime) > FwStagingTimeMax:
                    msg = f"FW copy operation exceeded the maximum time {FwStagingTimeMax} seconds."
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
                    StageFWOOB_Status = False
                    stage_msg = msg   

                msg = "{0}: GPU Deployment Time: {1} GPU Update Time: {2} \n Redfish Outcome: {3}".format(
                    MyName,
                    DeployTime - StartTime,
                    EndTime - StartTime,
                    json.dumps(JSONData, indent=4),
                )
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                # If task went to Exception, check if ALL failing components are in exclude_targets_list.
                # Some platforms (e.g. AMI BMC) cannot filter PLDM targets by chassis URI, so excluded
                # components (e.g. EROT) may still be attempted and may fail. If every failure message
                # names only an excluded component, treat staging as succeeded for the included components.
                if not StageFWOOB_Status and image_type not in self.NegativeTestImages:
                    exclude_list = self.dut().redfish_uri_config.get("GPU_FWUpdate", {}).get("exclude_targets_list", [])
                    if exclude_list and JSONData.get("TaskState") == "Exception":
                        task_messages = JSONData.get("Messages", [])
                        failure_msgs = [
                            m.get("Message", "")
                            for m in task_messages
                            if "failed" in m.get("Message", "").lower() or "exception" in m.get("Message", "").lower()
                        ]
                        if failure_msgs:
                            all_failures_excluded = all(
                                any(exc in msg for exc in exclude_list)
                                for msg in failure_msgs
                                if "failed" in msg.lower()
                            )
                            if all_failures_excluded:
                                msg = f"Task Exception but all failing components are in exclude_targets_list — treating staging as success."
                                self.test_run().add_log(LogSeverity.WARNING, msg)
                                StageFWOOB_Status = True

                if image_type in self.NegativeTestImages:
                    if "TaskState" in JSONData and "TaskStatus" in JSONData:
                        # For corrupt_component (F55/F56), corrupt (F23), and empty_metadata (F26):
                        # HMC stages valid components and marks the corrupt/invalid one as failed
                        # — task ends Completed (not Exception) with TaskStatus=Critical. Both
                        # Completed and Exception are valid outcomes when TaskStatus=Critical.
                        task_state_ok = (
                            JSONData["TaskState"] == "Exception"
                            or (image_type in ("corrupt_component", "corrupt", "empty_metadata") and JSONData["TaskState"] == "Completed")
                        )
                        if (
                            task_state_ok
                            and JSONData["TaskStatus"] == "Critical"
                        ):
                            msg = "Staging failed with as expected TaskState = {}, TaskStatus = {}".format(
                                JSONData["TaskState"], JSONData["TaskStatus"]
                            )
                            self.test_run().add_log(LogSeverity.DEBUG, msg)
                            if image_type == "corrupt_component":
                                StageFWOOB_Status = self.ctam_check_component_fwupd_failure(
                                    task_message_list=JSONData["Messages"],
                                    corrupted_component_id=corrupted_component_id
                                    )
                                if StageFWOOB_Status == False:
                                    stage_msg = "Non corrupt component staging failed!!"
                            else:
                                StageFWOOB_Status = True
                        else:
                            msg = "Staging failed but with an unexpected TaskState = {}, TaskStatus = {}".format(
                                JSONData["TaskState"], JSONData["TaskStatus"]
                            )
                            self.test_run().add_log(LogSeverity.DEBUG, msg)
                            StageFWOOB_Status = False
                            stage_msg = msg
            else:
                StageFWOOB_Status = True
        else:
            error_check = JSONData.get("error", None)
            if error_check and image_type != "large":
                message = JSONData.get("error", {}).get("@Message.ExtendedInfo", {})[0].get("MessageId", "")
                if not message:
                    message = JSONData.get("error", {}).get("code", "")
                resp_msg = self.dut().redfish_response_messages.get("UpdateProgress_Message", "UnexpectedMessage")
                if resp_msg:
                    if message.split(".")[-1].lower() == resp_msg.lower():
                        StageFWOOB_Status = False
                        stage_msg = "ExpectedMessage"
            
            elif image_type == "large":
                message = JSONData.get("error", {}).get("@Message.ExtendedInfo", {})[0].get("MessageId", "")
                if not message:
                    message = JSONData.get("error", {}).get("code", "")
                resp_msg = self.dut().redfish_response_messages.get("LargeFWImageUpdate", "PayloadTooLarge")
                if resp_msg:
                    if message.split(".")[-1].lower() != resp_msg.lower():
                        StageFWOOB_Status = False
                        stage_msg = "UnexpectedMessage"
                    else:
                        StageFWOOB_Status = True
        
            elif not image_type in self.NegativeTestImages:
                msg = "Staging failed with incorrect error message {}".format(
                    JSONData["error"]
                )
                self.test_run().add_log(LogSeverity.DEBUG, msg)

                StageFWOOB_Status = False
                stage_msg = msg
        return StageFWOOB_Status, stage_msg, FwUpdTaskID, staging_time

    def ctam_fw_update_verify(self, image_type="default", corrupted_component_id=None, specific_targets=[], version_check=True):
        """
        :Description:                   Firmware Update verification
        :param image_type:              Firmware image type
        :param corrupted_component_id:  ComponentIdentifier (in hex format) of the corrupted component image

        :returns:                       Update_Verified, string
        :rtype:                         Bool, string
        """
        MyName = __name__ + "." + self.ctam_fw_update_verify.__qualname__
        Update_Verified = True
        exception = False
        update_successful = []
        update_failed = []        
        failure_reason = ""
        self.ctam_get_fw_version(PostInstall=1)
        msg = json.dumps(self.PostInstallDetails, indent=4)
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        exclude_targets_list = self.dut().redfish_uri_config.get("GPU_FWUpdate", {}).get("exclude_targets_list", [])
        def _is_excluded(element_id):
            # Support both exact match and prefix match (for PLDM components with dynamic suffixes)
            return any(element_id == exc or element_id.startswith(exc) for exc in exclude_targets_list)
        if self.dut().dut_config.get("CompareFirmwareInventoryCount",{}).get("value", True):
            # Check if all components are reporting
            Update_Verified = self.ctam_compare_active_components_count()

        # Verify version of components currently reporting in FW inventory
        for element in self.PostInstallDetails:
            try:
                if _is_excluded(element["Id"]):
                    msg = f"Skipping {element['Id']} as it is in the exclude list"
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
                    continue
                negative_case = (
                    image_type == "negate" 
                    or str(element["Updateable"]).lower() == "false" # Note, this may mean empty SoftwareId. So this condition needs to come before the next one
                    or (image_type == "corrupt_component" and int(element["SoftwareId"], 16) == int(corrupted_component_id, 16) )
                    or (self.included_targets != []
                        and element["@odata.id"] not in self.included_targets)
                )
                if negative_case:
                    # FW version should be same as from pre-update
                    ExpectedVersion = self.PreInstallVersionDetails[element["Id"]]
                    msg = "FW should not be updated, expected version = {}".format(
                        ExpectedVersion
                    )
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
                
                elif specific_targets and element["Id"] not in specific_targets:
                    ExpectedVersion = self.PreInstallVersionDetails[element["Id"]]
                    
                else:
                    SoftwareId = str(hex(int(element["SoftwareId"], 16)))
                    # FW version should be updated per PLDM bundle
                    ExpectedVersion = self.PLDMComponentVersions(image_type=image_type).get(SoftwareId, '')
                msg = f"Post Install Details: {element['Id']} : {element['SoftwareId']} : {element.get('Version', 'NA')} : "
                if not ExpectedVersion:
                    # Either not present in PLDM bundle or not present in PreInstallVersionDetails
                    msg += "Not in the PLDM bundle"
                
                elif element.get("Version", '') not in ExpectedVersion:
                    # Both positive and negative test case
                    update_failed.append(element['SoftwareId'])
                    Update_Verified = False
                    msg += f"Update Failed : Expected {ExpectedVersion}"
                    failure_reason = f"Update Failed : Expected {ExpectedVersion}"

                elif negative_case:
                    # Negative test case, but expected.
                    msg += "Update Interrupted as Expected"
                
                else:
                    if not _is_excluded(element["Id"]):
                        if element["Status"]["Health"] != "OK" or element["Status"]["State"]!="Enabled":
                            update_failed.append(element['SoftwareId'])
                            Update_Verified = False
                            msg += f"Component Health/Status Failed : Expected Status['Health'] : OK and Status['State'] : Enabled"
                        else:
                            msg += "Update Successful"
                            update_successful.append(element['SoftwareId'])
                    else:
                        msg += "Update Successful"
                        update_successful.append(element['SoftwareId'])

                self.test_run().add_log(LogSeverity.DEBUG, msg)
            except Exception as e:
                failure_reason = " Exception occured: " + str(e)
                exception = True
                self.test_run().add_log(LogSeverity.ERROR, "Exception occured: " + str(e))
                Update_Verified = False

        if not version_check:
            if not exception and len(update_successful) > 0:
                Update_Verified = True
            else:
                Update_Verified = False
        msg = f"Updated Components count - {len(update_successful)} and Failed Components count - {len(update_failed)}"
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return Update_Verified, failure_reason
    
    def get_target_inventorys(self, targets):
        return [
            self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}"
                + "/UpdateService/FirmwareInventory/{}".format(element),
                component_type="GPU",
            )
            for element in targets
        ]

    def get_update_uri(self):
        """
        :Description:                   Get supported fwupdate uri, multipart push uri over httpush
        :returns:                       whether uri was found, update uri and if it supports multipart push
        :rtype:                         Bool, Str, Bool
        """
        
        uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )
        response = self.dut().run_redfish_command(uri=uri, mode="GET")
        if 'MultipartHttpPushUri' in response.dict and self.dut().multipart_push_uri_support:
            return True, response.dict['MultipartHttpPushUri'], True
        
        elif 'HttpPushUri' in response.dict:
            return True, response.dict['HttpPushUri'], False
            # return True, uri, False  #FIXME Once we have product compliance, we will uncomment the above line.
        return False, "", False

    def ctam_pushtargets(self, targets=[], is_multipart_uri=False):
        if is_multipart_uri:
            return True
        MyName = __name__ + "." + self.ctam_pushtargets.__qualname__
        PushSuccess = False
        targets = self.get_target_inventorys(targets)
        Payload = {"HttpPushUriTargets": targets}

        v1_str = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )

        response = self.dut().run_redfish_command(uri=v1_str, mode="PATCH", body=Payload)

        JSONData = response.dict

        if jsondeephunt(JSONData, "Message") == "The request completed successfully.":
            JSONData = self.ctam_getus()
            if str(JSONData["HttpPushUriTargets"]) == str(targets):
                PushSuccess = True
                self.included_targets = targets

                msg = f"Myname: {MyName} and Included Targets: {self.included_targets}"
                self.test_run().add_log(LogSeverity.DEBUG, msg)
            else:
                msg = f"MyName: {MyName} and HttpPushUriTargets: {JSONData['HttpPushUriTargets']}"
                self.test_run().add_log(LogSeverity.DEBUG, msg)

                print("{} {}".format(MyName, str(targets)))
        return PushSuccess

    def RedFishFWUpdate(self, BinPath, URI, targets=[], is_multipart=False, is_force_update=True):
        """
        :Description:         It will update system firmware using redfish command.
        :param BinPath:       Path for the bin
        :param URI:           URI for creating URL

        :returns:             JSON data after executing redfish command
        :rtype:               JSON Dict
        """
        MyName = __name__ + "." + self.RedFishFWUpdate.__qualname__
        JSONData = {}

        if is_multipart:
            headers = {"Content-Type": "multipart/form-data"}
            body = {
                "UpdateFile": (BinPath, open(BinPath, "rb"), "application/octet-stream"),
                "UpdateParameters" : ("Targets", json.dumps({"Targets": targets, "ForceUpdate": True if is_force_update else False}),'application/json')
            }
            response = self.dut().run_request_command(uri=URI, mode="POST",files=body, body={})
            JSONData = response.json()
        elif self.dut().multipart_form_data:
            # Unstructured HTTP push update
            files=[
                ('UpdateFile',(BinPath,open(BinPath,'rb'),'application/octet-stream'))
                ]
            response = self.dut().run_request_command(uri=URI, mode="POST", body={}, headers=None, files=files)
            JSONData = response.json()
        else:
            headers = {"Content-Type": "application/octet-stream"}
            body = open(BinPath, "rb").read()
            response = self.dut().run_request_command(uri=URI, mode="POST", body=body, headers=headers)
            JSONData = response.json()
        msg = "{0}: RedFish Input: {1} Result: {2}".format(MyName, BinPath, JSONData)
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        return JSONData

    def ctam_build_updatable_device_list(self, illegal=0):
        MyName = __name__ + "." + self.ctam_build_updatable_device_list.__qualname__
        JSONData = self.ctam_getfi(expanded=1)
        updateable_devices = []
        true = True
        false = False
        if not illegal:
            jsonhuntall(JSONData, "Updateable", true, "Id", updateable_devices)
        else:
            jsonhuntall(JSONData, "Updateable", false, "Id", updateable_devices)
        if updateable_devices == []:
            self.test_run().add_log(LogSeverity.DEBUG, "No updatable devices found")
        return updateable_devices


    def ctam_get_updateable_devices_in_bundle(self, image_type="default", illegal=0):
        devices = []
        # get list of updatable device
        updateable_devices = self.ctam_build_updatable_device_list(illegal=illegal)
        if not updateable_devices:
            return devices
        # check if the updateable device is present in pldm
        self.ctam_get_fw_version(PostInstall=0)
        for device in self.PreInstallDetails:
            if device["Id"] not in updateable_devices: #skip if not updateable
                continue
            if self.PLDMComponentVersions(image_type=image_type).get(device["SoftwareId"]):
                devices.append(device)
        return [] if not devices else [item['Id'] for item in devices]


    def ctam_selectpartiallist(self, count=0, excluded_targets=[], specific_targets=[], illegal=0):
        MyName = __name__ + "." + self.ctam_selectpartiallist.__qualname__
        PartialDeviceSelected = True
        _, _, is_multipart_uri = self.get_update_uri()
        self.ctam_pushtargets(is_multipart_uri=is_multipart_uri)
        device_list = self.ctam_build_updatable_device_list(illegal=illegal)
        if specific_targets == []:
            if count == 0:
                count = len(device_list)
            device_list_new = [device for device in device_list if not device in excluded_targets]
            if not device_list_new:
                return True
            RandomListOfDevices = random.choices(device_list_new, k=random.randint(1, count))
            self.test_run().add_log(LogSeverity.INFO, str(RandomListOfDevices))
            if self.ctam_pushtargets(RandomListOfDevices, is_multipart_uri=is_multipart_uri):
                PartialDeviceSelected = RandomListOfDevices
        else:
            if all(device in device_list for device in specific_targets):
                PartialDeviceSelected = specific_targets
                self.ctam_pushtargets(specific_targets, is_multipart_uri=is_multipart_uri)
            else:
                PartialDeviceSelected = None
                msg = f"specific_targets {specific_targets} is not available in Device list {device_list}"
                self.test_run().add_log(LogSeverity.INFO, msg)
            JSONData = self.ctam_getus()
        return PartialDeviceSelected

    def ctam_get_component_to_be_corrupted(self, VendorProvidedBundle=True):
        """
        :Description:                   It will check the package_info.json for CorruptComponentIdentifier.
                                        If both corrupt package and CorruptComponentIdentifier are not provided,
                                        it'll find the first updatable element from firmware inventory.

        :param VendorProvidedBundle:    Boolean value indicating if the vendor is required to provide a corrupt bundle.
                                        True by default.

        :returns:                       SoftwareID of the component to be corrupted (in hex format)
        :rtype:                         str. None in case of failure
        """
        MyName = __name__ + "." + self.ctam_get_component_to_be_corrupted.__qualname__
        vendor_provided_corrupt_pkg = self.dut().package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("Package", "")
        if VendorProvidedBundle and vendor_provided_corrupt_pkg == "":
            msg = "Missing corrupt bundle name in package info file."
            self.test_run().add_log(LogSeverity.ERROR, msg)
            corrupt_component_id = None

        else:
            corrupt_component_id = self.dut().package_config.get("GPU_FW_IMAGE_CORRUPT_COMPONENT", {}).get("CorruptComponentIdentifier", "")
            if corrupt_component_id == "":
                if VendorProvidedBundle:
                    msg = "CorruptComponentIdentifier must be provided for bundle {package_name}."
                    self.test_run().add_log(LogSeverity.ERROR, msg)
                    corrupt_component_id = None
                else:
                    JSONData = self.ctam_getfi(expanded=1)
                    for element in JSONData["Members"]:
                        if str(element["Updateable"]) == "True":
                            corrupt_component_id = element["SoftwareId"]
                            break
            msg = f"{MyName} returned component ID to be corrupted: {corrupt_component_id}"
            self.test_run().add_log(LogSeverity.DEBUG, msg)

        return corrupt_component_id

    def ctam_check_component_fwupd_failure(self, task_message_list, corrupted_component_id):
        """
        :Description:                       It will check if the task status message list is showing the
                                            corrupted component update failed and all other component
                                            copying (staging) went through.

        :param task_message_list:           List of message from the task status response
        :param corrupted_component_id:      ComponentIdentifier (in hex format) of the corrupted component image

        :returns:                           NonCorruptCompStaging_Success
        :rtype:                             Bool
        """
        MyName = __name__ + "." + self.ctam_check_component_fwupd_failure.__qualname__
        NonCorruptCompStaging_Success = True

        corrupted_component_list = self.ctam_get_component_list(corrupted_component_id)

        for message in task_message_list:
            # Check if the component is not corrupted, but the severity is not OK
            # Redfish uses "MessageSeverity"; fall back to "Severity" for older BMCs
            severity = message.get("MessageSeverity") or message.get("Severity", "OK")
            if (not any(item in corrupted_component_list for item in message["MessageArgs"])) \
                and "Update" in message["MessageId"] \
                and severity != "OK":
                    NonCorruptCompStaging_Success = False
                    return

        return NonCorruptCompStaging_Success

    def ctam_get_component_list(self, component_id):
        """
        :Description:                       It will check FW Inventory and find all the components with
                                            the provided component ID.

        :param component_id:                Component ID / SoftwareID

        :returns:                           List of components with the component ID
        :rtype:                             list
        """
        JSONData = self.ctam_getfi(expanded=1)
        component_list = []
        jsonhuntall(JSONData, "SoftwareId", component_id, "Id", component_list)
        return component_list

    def ctam_compare_active_components_count(self):
        """
        :Description:                       It will compare FW Inventory from Pre and Post Fw update
                                            to make sure all components have come back online. Raises exception
                                            if pre install and post install details are empty. Make sure to
                                            call ctam_get_fw_version method to fill up pre and post install details.

        :returns:                           AllComponentsActive
        :rtype:                             Bool
        """

        if not self.PreInstallDetails or not self.PostInstallDetails:
            raise RuntimeError(f"Pre and Post install details are missing.\
                Post install version details are {self.PostInstallVersionDetails}\
                    and Pre install details are {self.PreInstallVersionDetails}")

        elif len(self.PreInstallDetails) != len(self.PostInstallDetails): # FIXME: Chances are post-intall < pre-install. Any chances of post-install > pre-install?
            AllComponentsActive = False
            msg = "Mismatch in number of components. Update Failed : Pre-install count {} != Post-install count {} ".format(
                len(self.PreInstallDetails),
                len(self.PostInstallDetails),
            )
            self.test_run().add_log(LogSeverity.DEBUG, msg)

        else:
            AllComponentsActive = True

        return AllComponentsActive

    def ctam_get_version_from_bundle(self, image_type):
        """
        :Description:           Check PLDM bundle json for FW version by software id.
                                If JSON not provided for N/N-1, extract from fwpkg and write
                                <fwpkg_basename>_header.json to run output dir.

        :param image_type:      image type

        :returns:               ComponentVersions
        :rtype:                 string
        """
        ComponentIdsAndVersions = {}
        PLDMPkgJson = {}

        dut = self.dut()
        test_run = self.test_run()
        PLDMPkgJson_file = self.get_PLDMPkgJson_file(image_type=image_type)

        # N/N-1: if JSON missing, extract header from bundle and save to run output dir
        if not PLDMPkgJson_file or not os.path.isfile(PLDMPkgJson_file):
            fwpkg_path = self.get_fwpkg_path(image_type=image_type)

            if fwpkg_path and os.path.isfile(fwpkg_path):
                try:
                    pldm_parser = PLDMUnpack(fwpkg_path)

                    if pldm_parser.parse_pldm_package():
                        pldm_parser.get_full_metadata_json()
                        basename = os.path.basename(fwpkg_path)
                        header_path = os.path.join(dut.output_dir,
                                                    f"{basename}_header.json")

                        with open(header_path, "w") as f:
                            json.dump(pldm_parser.full_header, f, indent=4, sort_keys=False)

                        test_run.add_log(LogSeverity.INFO,
                                        f"Extracted PLDM header from bundle to {header_path}")
                        PLDMPkgJson_file = header_path
                    else:
                        test_run.add_log(LogSeverity.WARNING,
                                        f"Failed to parse PLDM package for header: {fwpkg_path}")
                except (IOError, OSError) as e:
                    test_run.add_log(LogSeverity.WARNING,
                                    f"Header extraction failed ({fwpkg_path}): {e}")
            else:
                test_run.add_log(LogSeverity.DEBUG,
                                f"Fwpkg not found for image_type={image_type}, skipping header extraction")

        # Load JSON if available
        if PLDMPkgJson_file and os.path.isfile(PLDMPkgJson_file):
            with open(PLDMPkgJson_file, "r") as f:
                PLDMPkgJson = json.load(f)

        jsonmultivaluehunt(PLDMPkgJson, "ComponentIdentifier",
                            "ComponentVersionString", ComponentIdsAndVersions)

        ComponentIdsAndVersions = {
            str(hex(int(key, 16))): value
            for key, value in ComponentIdsAndVersions.items()
        }

        return ComponentIdsAndVersions
