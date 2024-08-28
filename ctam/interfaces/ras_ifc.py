"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""

from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc
import time
import json
from ocptv.output import LogSeverity
from utils.json_utils import *
try:
    from internal_interfaces.ras_ifc_int import RasIfcInt as Meta
except:
    from utils.ctam_utils import MetaNull as Meta

class RasIfc(FunctionalIfc, metaclass=Meta):
    
    def __init__(self):
        super().__init__()

    
    def ctam_discover_crashdump_cap(self):
        """
        :Description:				Get CollectDiagnosticDataActionInfo 

        :returns:				    List of all action uris with LogService.CollectDiagnosticData
        """
        collectdiagnostic_uri_list = []
        logservice_ras_uri_list = self.ctam_get_collectdiagnostic_logservices_uris()
        for uri in logservice_ras_uri_list:
            self.ctam_redfish_uri_deep_hunt(URI=uri, uri_hunt="LogService.CollectDiagnosticData", uri_listing=collectdiagnostic_uri_list, uri_analyzed=[], action=1)
        self.write_test_info("{}".format(collectdiagnostic_uri_list))
        return collectdiagnostic_uri_list
    
    def ctam_get_collectdiagnostic_logservices_uris(self):
        """
        :Description:				Similar to logservice uri list under health check interface, but only for systems and managers. 

        :returns:				    List of all URIs with "LogServices" as a property under /redfish/v1/Managers and /redfish/v1/Systems
        """
        collectdiagnostic_logservices_uri_list=[]
        self.ctam_redfish_uri_deep_hunt("/redfish/v1/Managers", "LogServices", collectdiagnostic_logservices_uri_list, uri_analyzed=[])
        self.ctam_redfish_uri_deep_hunt("/redfish/v1/Systems", "LogServices", collectdiagnostic_logservices_uri_list, uri_analyzed=[])
        self.write_test_info("{}".format(collectdiagnostic_logservices_uri_list))
        return collectdiagnostic_logservices_uri_list
            
    def ctam_collect_crashdump_manager_list(self):
        collect_managers_list = []
        crashdump_uri_list = self.ctam_discover_crashdump_cap()
        collect_managers_list = [uri for uri in crashdump_uri_list if "/redfish/v1/Managers" in uri]
        # for uri in crashdump_uri_list:
        #     if "/redfish/v1/Managers" in uri:
        #         collect_managers_list.append(uri)
        return collect_managers_list
    
    def check_location_list(self, JSONData):
        """_summary_

        Args:
            JSONData (_type_): _description_

        Returns:
            _type_: _description_
        """
        location_list = JSONData.get("Payload", {}).get("HttpHeaders", [])
        if not location_list:
            self.test_run().add_log(LogSeverity.FATAL, "Location list is not found")
            return ""
        
        location = location_list[-1].split(": ")[-1]
        if not location:
            self.test_run().add_log(LogSeverity.FATAL, "Location list is not found")
            return ""
        
        self.test_run().add_log(LogSeverity.INFO, "Location is: {}".format(location))
        
        location_uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}" + "{}".format(location), component_type="GPU")
        self.test_run().add_log(LogSeverity.INFO, "Location URI is: {}".format(location_uri))
        response = self.dut().run_redfish_command(uri=location_uri)
        if not response.status in range(200,202):
            self.test_run().add_log(LogSeverity.FATAL, "URI doesn't exist")
            return ""
        
        self.test_run().add_log(LogSeverity.INFO, "{} URI exist ".format(location_uri))
        return location_uri
            

    def ctam_crashdump_task_status(self,wait_for_task_completion=True):
        Task_completion_Status = False
        location_uri = ""
        for uri in self.ctam_collect_crashdump_manager_list():
            body = {"DiagnosticDataType": "Manager"}
            headers = {"Content-Type": "application/json"}
            url = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}" + "{}".format(uri), component_type="GPU")
            response = self.dut().run_redfish_command(uri=url, mode="POST", body=body, headers=headers)
            if "error" not in response.dict:
                if wait_for_task_completion:
                    TaskID = response.dict["Id"]
                    if self.dut().is_debug_mode():
                            self.test_run().add_log(LogSeverity.DEBUG, TaskID)
                    Task_completion_Status, MonitorJSONData = self.ctam_monitor_task(TaskID)
                    location_uri = self.check_location_list(MonitorJSONData)                                
        return Task_completion_Status, location_uri

    def ctam_download_crashdump_attachment(self):
        result = False
        status, location_uri = self.ctam_crashdump_task_status()
        if status and location_uri:
            # location_uri = self.check_location_list()
            if self.RedfishDownloadDump(location_uri):
                self.test_run().add_log(LogSeverity.INFO, "Dump is downloaded.")
                result = True
            else:
                self.test_run().add_log(LogSeverity.INFO, "Dump download Failed.")
                result = False
        else:
            self.test_run().add_log(LogSeverity.FATAL, "Empty list or dictionary.")
            result = False
        return result