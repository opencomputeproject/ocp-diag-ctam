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
        self.collectdiagnostic_uri_list = []
        self.logdump_uri_list = []
        self.dumplog_uri_list = []
        self.JSONData = {}
    
    def ctam_discover_crashdump_cap(self):
        """
        :Description:				Get CollectDiagnosticDataActionInfo 

        :returns:				    List of all action uris with LogService.CollectDiagnosticData
        """
        self.collectdiagnostic_uri_list = []
        self.logservice_ras_uri_list = self.ctam_get_collectdiagnostic_logservices_uris()
        for uri in self.logservice_ras_uri_list:
            self.ctam_redfish_uri_deep_hunt(URI=uri, uri_hunt="LogService.CollectDiagnosticData", uri_listing = self.collectdiagnostic_uri_list, uri_analyzed=[], action=1)
        self.write_test_info("{}".format(self.collectdiagnostic_uri_list))
        return self.collectdiagnostic_uri_list
    
    def ctam_get_collectdiagnostic_logservices_uris(self):
        """
        :Description:				Similar to logservice uri list under health check interface, but only for systems and managers. 

        :returns:				    List of all URIs with "LogServices" as a property under /redfish/v1/Managers and /redfish/v1/Systems
        """
        self.collectdiagnostic_logservices_uri_list=[]
        self.ctam_redfish_uri_deep_hunt("/redfish/v1/Managers", "LogServices", self.collectdiagnostic_logservices_uri_list, uri_analyzed=[])
        self.ctam_redfish_uri_deep_hunt("/redfish/v1/Systems", "LogServices", self.collectdiagnostic_logservices_uri_list, uri_analyzed=[])
        self.write_test_info("{}".format(self.collectdiagnostic_logservices_uri_list))
        return self.collectdiagnostic_logservices_uri_list
            
    def ctam_collect_crashdump_manager_list(self):
        self.collect_managers_list = []
        self.crashdump_uri_list = self.ctam_discover_crashdump_cap()
        for uri in self.crashdump_uri_list:
            if "/redfish/v1/Managers" in uri:
                self.collect_managers_list.append(uri)
        return self.collect_managers_list

    def ctam_crashdump_task_status(self):
        wait_for_task_completion = True
        Task_completion_Status = False
        for uri in self.ctam_collect_crashdump_manager_list():
            body = {"DiagnosticDataType": "Manager"}
            headers = {"Content-Type": "application/json"}
            url = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}" + "{}".format(uri), component_type="GPU")
            response = self.dut().run_redfish_command(uri=url, mode="POST", body=body, headers=headers)
            self.JSONData = response.dict
            if "error" not in self.JSONData:
                if wait_for_task_completion:
                    TaskID = self.JSONData["Id"]
                    if self.dut().is_debug_mode():
                            self.test_run().add_log(LogSeverity.DEBUG, TaskID)
                    Task_completion_Status, self.JSONData = self.ctam_monitor_task(TaskID)
        return Task_completion_Status

    def ctam_download_crashdump_attachment(self):
        result = False
        if self.ctam_crashdump_task_status():
            location_list = self.JSONData.get("Payload", {}).get("HttpHeaders", [])
            if location_list:
                location = location_list[-1].split(": ")[-1]
                location_uri = self.dut().uri_builder.format_uri(redfish_str="{GPUMC}" + "{}".format(location), component_type="GPU")
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