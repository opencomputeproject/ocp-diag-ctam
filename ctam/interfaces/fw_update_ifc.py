"""
Copyright (c) Microsoft Corporation
Copyright (c) NVIDIA CORPORATION

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""
import os
import json
import time
import random
from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc
from ocptv.output import LogSeverity
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
        :Description:				Get Firmware Version
        :param PostInstall:		Get Version after install the Firmware or before installing

        :returns:				    None
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
        :Description:				Check Firmware before installation
        :param image_type:		    Type of the Firmware image

        :returns:				    VersionsDifferent
        :rtype: 					Bool
        """
        MyName = __name__ + "." + self.ctam_fw_update_precheck.__qualname__
        VersionsDifferent = True
        status_message = ""
        # if all component is update not needed then return update not needed. If any one component is updatable return updatable
        self.ctam_get_fw_version(PostInstall=0)
        for element in self.PreInstallDetails:
            # Check ONLY the ones which are part of HttpPushURITargets
            if (
                self.included_targets == []
                or element["@odata.id"] in self.included_targets
            ):
                msg = f"Pre Install Details: {element['Id']} : {element['SoftwareId']} : {element['Version']} : "
                if str(element["Updateable"]) == "True":
                    Package_Version = self.PLDMComponentVersions(image_type=image_type).get(element["SoftwareId"])
                    if Package_Version is None:
                        msg += "Not in the PLDM bundle"
                    
                    elif element["Version"] != Package_Version and (
                        self.included_targets == []
                        or element["@odata.id"] in self.included_targets
                    ):
                        VersionsDifferent = False
                        msg += f"Update Capable to {Package_Version}"

                    else:
                        msg += "Update Not Needed."
                else:
                    msg += "Not Updateable."
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                    
            else:
                # Not in HttpPushURITargets
                pass
            
        return VersionsDifferent, status_message

    def ctam_stage_fw(
        self, partial=0, image_type="default", wait_for_stage_completion=True,
        corrupted_component_id=None, corrupted_component_list=[],
        check_time=False
    ):
        """
        :Description:							Stage Firmware
        :param partial:							Partial
        :param image_type:						Type of Firmware Image
        :param wait_for_stage_completion:		Wait for stage completion
        :param corrupted_component_id:          ComponentIdentifier of the component image to be corrupted for specific negative tests
        :param corrupted_component_list:        List component names (Ids) which are corrupted
        :param check_time:                      Check the staging time does not exceed maximum time per spec

        :returns:				    			StageFWOOB_Status, StageFWOOB_Status_message, return_task_id 
        :rtype: 								Bool, str, str
        """
        MyName = __name__ + "." + self.ctam_stage_fw.__qualname__
        StartTime = time.time()
        pushtargets = self.dut().uri_builder.format_uri(redfish_str="{HttpPushUriTargets}", component_type="GPU")
        if partial == 0 and pushtargets:
            self.ctam_pushtargets()
        JSONFWFilePayload = self.get_JSONFWFilePayload_file(image_type=image_type, corrupted_component_id=corrupted_component_id)
        if not os.path.isfile(JSONFWFilePayload):
            self.test_run().add_log(LogSeverity.DEBUG, f"Package file not found at path {JSONFWFilePayload}!!!")
            return False, "", ""
        if self.dut().is_debug_mode():
            print(JSONFWFilePayload)
        uri = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )
        if self.dut().is_debug_mode():
            self.test_run().add_log(LogSeverity.DEBUG, f"URI : {uri}")
        
        JSONData = self.RedFishFWUpdate(JSONFWFilePayload, uri)
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
                if check_time and (EndTime - StagingStartTime) > FwStagingTimeMax:
                    msg = f"FW copy operation exceeded the maximum time {FwStagingTimeMax} seconds."
                    self.test_run().add_log(LogSeverity.DEBUG, msg)
                    StageFWOOB_Status = False

                msg = "{0}: GPU Deployment Time: {1} GPU Update Time: {2} \n Redfish Outcome: {3}".format(
                    MyName,
                    DeployTime - StartTime,
                    EndTime - StartTime,
                    json.dumps(JSONData, indent=4),
                )
                self.test_run().add_log(LogSeverity.DEBUG, msg)
                if image_type in self.NegativeTestImages:
                    if "TaskState" in JSONData and "TaskStatus" in JSONData:
                        if (
                            JSONData["TaskState"] == "Exception"
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
                            else:
                                StageFWOOB_Status = True
                        else:
                            msg = "Staging failed but with an unexpected TaskState = {}, TaskStatus = {}".format(
                                JSONData["TaskState"], JSONData["TaskStatus"]
                            )
                            self.test_run().add_log(LogSeverity.DEBUG, msg)
                            StageFWOOB_Status = False
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
                    if message.split(".")[-1].lower() != resp_msg.lower():
                        StageFWOOB_Status = False
                        stage_msg = "UnexpectedMessage"
            
            if image_type == "large":
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
        return StageFWOOB_Status, stage_msg, FwUpdTaskID

    def ctam_fw_update_verify(self, image_type="default", corrupted_component_id=None):
        """
        :Description:				    Firmware Update verification
        :param image_type:			    Firmware image type
        :param corrupted_component_id:  ComponentIdentifier (in hex format) of the corrupted component image

        :returns:				        Update_Verified
        :rtype: 					    Bool
        """
        MyName = __name__ + "." + self.ctam_fw_update_verify.__qualname__
        Update_Verified = True

        self.ctam_get_fw_version(PostInstall=1)
        msg = json.dumps(self.PostInstallDetails, indent=4)
        self.test_run().add_log(LogSeverity.DEBUG, msg)
        
        # Check if all components are reporting
        Update_Verified = self.ctam_compare_active_components_count()

        # Verify version of components currently reporting in FW inventory
        for element in self.PostInstallDetails:
            negative_case = (
                image_type == "negate" 
                or str(element["Updateable"]) == "False" # Note, this may mean empty SoftwareId. So this condition needs to come before the next one
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
                
            else:
                # FW version should be updated per PLDM bundle
                ExpectedVersion = self.PLDMComponentVersions(image_type=image_type).get(element["SoftwareId"])
            
            msg = f"Post Install Details: {element['Id']} : {element['SoftwareId']} : {element['Version']} : "
            if ExpectedVersion is None:
                # Either not present in PLDM bundle or not present in PreInstallVersionDetails
                msg += "Not in the PLDM bundle"
            
            elif element["Version"] != ExpectedVersion:
                # Both positive and negative test case
                Update_Verified = False
                msg += f"Update Failed : Expected {ExpectedVersion}"

            elif negative_case:
                # Negative test case, but expected.
                msg += "Update Interrupted as Expected"
            
            else:
                msg += "Update Successful"
                
            self.test_run().add_log(LogSeverity.DEBUG, msg)

        return Update_Verified

    def ctam_pushtargets(self, targets=[]):
        MyName = __name__ + "." + self.ctam_pushtargets.__qualname__
        PushSuccess = False
        targets = [
            self.dut().uri_builder.format_uri(
                redfish_str="{BaseURI}"
                + "/UpdateService/FirmwareInventory/{}".format(element),
                component_type="GPU",
            )
            for element in targets
        ]
        Payload = {"HttpPushUriTargets": targets}

        v1_str = self.dut().uri_builder.format_uri(
            redfish_str="{BaseURI}/UpdateService", component_type="GPU"
        )

        response = self.dut().run_redfish_command(uri=v1_str, mode="PATCH", body=Payload)

        JSONData = response.dict

        #print(json.dumps(JSONData, indent=4))

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

    def RedFishFWUpdate(self, BinPath, URI):
        """
        :Description:         It will update system firmware using redfish command.
        :param BinPath:		  Path for the bin
        :param URI:		      URI for creating URL

        :returns:		      JSON data after executing redfish command
        :rtype:               JSON Dict
        """
        MyName = __name__ + "." + self.RedFishFWUpdate.__qualname__
        FileName = BinPath
        JSONData = {}
        URL = URI  # + '"' + FileName + '"'
        if self.dut().redfish_uri_config.get("GPU", {}).get("UnstructuredHttpPush", False):
            # Unstructured HTTP push update
            if self.dut().multipart_form_data:
                headers = None
                body = {}
                files=[
                    ('UpdateFile',(FileName,open(FileName,'rb'),'application/octet-stream'))
                    ]
                response = self.dut().run_request_command(uri=URL, mode="POST", body=body, headers=headers, files=files)
                JSONData = response.json()
            else:
                headers = {"Content-Type": "application/octet-stream"}
                body = open(FileName, "rb").read()
                response = self.dut().run_redfish_command(uri=URL, mode="POST", body=body, headers=headers)
                JSONData = response.dict
        else:
                headers = {"Content-Type": "multipart/form-data"}
                body = {}
                body["UpdateFile"] = (
                    FileName,
                    open(FileName, "rb"),
                    "application/octet-stream",
                )
                response = self.dut().run_redfish_command(uri=URL, mode="POST", body=body, headers=headers)
                JSONData = response.dict
        msg = "{0}: RedFish Input: {1} Result: {2}".format(MyName, FileName, JSONData)
        # msg_2 = "FW Update URL = {}".format(URL)
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

    def ctam_selectpartiallist(self, count=0, excluded_targets=[], specific_targets=[], illegal=0):
        MyName = __name__ + "." + self.ctam_selectpartiallist.__qualname__
        PartialDeviceSelected = True
        self.ctam_pushtargets()
        device_list = self.ctam_build_updatable_device_list(illegal)
        if specific_targets == []:
            if count == 0:
                count = len(device_list)
            device_list_new = [device for device in device_list if not device in excluded_targets]
            RandomListOfDevices = random.choices(device_list_new, k=random.randint(1, count))
            self.test_run().add_log(LogSeverity.INFO, str(RandomListOfDevices))
            if self.ctam_pushtargets(RandomListOfDevices):
                PartialDeviceSelected = RandomListOfDevices
        else:
            if all(device in device_list for device in specific_targets):
                PartialDeviceSelected = specific_targets
                self.ctam_pushtargets(specific_targets)
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
        
        :returns:		                SoftwareID of the component to be corrupted (in hex format)
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

        :returns:				    	    NonCorruptCompStaging_Success
        :rtype:                             Bool
        """
        MyName = __name__ + "." + self.ctam_check_component_fwupd_failure.__qualname__        
        NonCorruptCompStaging_Success = True
        
        corrupted_component_list = self.ctam_get_component_list(corrupted_component_id)
        
        for message in task_message_list:
            # Check if the component is not corrupted, but the severity is not OK
            if (not any(item in corrupted_component_list for item in message["MessageArgs"])) \
                and "Update" in message["MessageId"] \
                and message["Severity"] != "OK":
                    NonCorruptCompStaging_Success = False
                    return
            
        return NonCorruptCompStaging_Success
    
    def ctam_get_component_list(self, component_id):
        """
        :Description:                       It will check FW Inventory and find all the components with
                                            the provided component ID.
        
        :param component_id:                Component ID / SoftwareID

        :returns:				    	    List of components with the component ID
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

        :returns:				    	    AllComponentsActive
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
        :Description:           It will check the PLDM bundle json and find FW version
                                of the component with the specified software id.
        
        :param image_type:		image type

        :returns:				ComponentVersions
        :rtype:                 string
        """
        ComponentVersions = {}
        
        # First, get list of SoftwareIds of all the updatable components
        FWInventory = self.ctam_getfi(expanded=1)
        Updateable_SoftwareIds = []
        jsonhuntall(FWInventory, "Updateable", True, "SoftwareId", Updateable_SoftwareIds)
        Updateable_SoftwareIds = list(set(Updateable_SoftwareIds)) # Remove duplicates
        Updateable_SoftwareIds[:] = (SwId for SwId in Updateable_SoftwareIds if SwId != "") # FIXME: Temporary: Remove empty Software IDs
        
        # Then get the PLDM bundle json
        PLDMPkgJson_file = self.get_PLDMPkgJson_file(image_type=image_type)
        # check again above code
        if PLDMPkgJson_file and os.path.isfile(PLDMPkgJson_file):
            with open(PLDMPkgJson_file, "r") as f:
                PLDMPkgJson = json.load(f)
            # Now find the FW version for the software IDs in the PLDM bundle
            
            for software_id in Updateable_SoftwareIds:
                fw_versions = []

                jsonhuntall(PLDMPkgJson,
                        "ComponentIdentifier",
                        str(int(software_id, 16)),
                        "ComponentVersionString",
                        fw_versions
                    )
                if not len(fw_versions):
                # Component is not present in PLDM bundle
                    ComponentVersions[software_id] = None
                elif len(fw_versions) == 1:
                    # Only one image is present for this component in the PLDM bundle
                    ComponentVersions[software_id] = fw_versions[0]
                else:
                    # There are multiple images for the same component.
                    # Additional SKU mapping is needed to find the correct version
                    # FIXME: This implementation is deeply tied to format of the PLDM bundle json. Can we utilize PLDMUnpack class?
                    ComponentRelatedItemList = jsonhunt(FWInventory,
                                                "SoftwareId",
                                                software_id,
                                                "RelatedItem",
                                            )
                    for related_item in ComponentRelatedItemList:
                        related_item_uri = related_item.get("@odata.id")
                        if related_item_uri:
                            response = self.dut().run_redfish_command(uri=related_item_uri)
                            data = response.dict
                            component_sku = data.get("SKU")
                            if component_sku:
                                ApplicableComponents = []
                                for DeviceRecord in PLDMPkgJson.get("FirmwareDeviceIdentificationArea", {}).get("FirmwareDeviceIDRecords", {}):
                                    for descriptor in DeviceRecord["RecordDescriptors"]:
                                        if "SKU" in descriptor.get("VendorDefinedDescriptorTitleString", "")\
                                            and int(descriptor.get("VendorDefinedDescriptorData"), 16) == int(component_sku, 16):
                                                ApplicableComponents = DeviceRecord["ApplicableComponents"]
                                                break
                                    if ApplicableComponents:
                                        break
                                for comp_index in ApplicableComponents:
                                    comp_info =  PLDMPkgJson.get("ComponentImageInformationArea", {}).get("ComponentImageInformation", [])[comp_index]
                                    if comp_info["ComponentIdentifier"] == str(hex(int(software_id, 16))):
                                        ComponentVersions[software_id] = comp_info["ComponentVersionString"]
                                        break
        else:
            msg = "PLDMPkgJson file not found."
            self.test_run().add_log(LogSeverity.DEBUG, msg)   
            raise Exception("PLDMPkgJson file not found.") 
        return ComponentVersions
    
    # def ctam_delay_between_testcases(self):
    #     MyName = __name__ + "." + self.ctam_delay_between_testcases.__qualname__
    #     IdleWaitTime = self.dut().dut_config["IdleWaitTimeAfterFirmwareUpdate"]["value"]
    #     msg = f"Execution will be delayed by {IdleWaitTime} seconds."
    #     self.test_run().add_log(LogSeverity.INFO, msg)
    #     time.sleep(IdleWaitTime)
    #     msg = f"Execution is delayed successfully by {IdleWaitTime} seconds."
    #     self.test_run().add_log(LogSeverity.INFO, msg)
    #     return True