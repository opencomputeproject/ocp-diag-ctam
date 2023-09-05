"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""

from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc
from ocptv.output import LogSeverity
from utils.json_utils import *

class RasIfc(FunctionalIfc):

    _instance: Optional["RasIfc"] = None

    def __new__(cls, *args, **kwargs):
        """
        ensure only 1 instance can be created

        :return: instance
        :rtype: FWUpdateIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = super(RasIfc, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.collectdiagnostic_uri_list = []
        self.logdump_uri_list = []
        self.dumplog_uri_list = []
        

    @classmethod
    def get_instance(cls, *args, **kwargs):
        """
        if there is an existing instance, return it, otherwise create the singleton instance and return it

        :return: instance
        :rtype: FWUpdateIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = cls(*args, **kwargs)
        return cls._instance
    
    def ctam_redfish_hunt(self, URI, member_hunt="", uri_listing=[]):
        """
        :Description:			CTAM Redfish hunt - a recursive function to look deep til we find the member to hunt
        :param URI:             The uri under which we are searching for the member to hunt (type string)
        :param member_hunt:     Json member we are hunting for (type string).
        :param uri_listing:     An array that will eventually contain a list of all URIs that house the member to hunt.

        :returns:				None
        """
        response = self.dut().run_redfish_command(uri="{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
        JSONData = response.dict
        if member_hunt in JSONData:
            uri_listing.append(URI)
            return
        if "Members" in JSONData:
            i = 0
            for element in JSONData["Members"]:
                if "@odata.id" in element:
                    URI = JSONData["Members"][i]["@odata.id"]
                    self.ctam_redfish_hunt(URI, member_hunt, uri_listing)
                    i = i + 1

    def ctam_get_dump_uris(self): #FIXME
        target_values = []

        for entry in self.ctam_get_collectdiagnostic_uris():
            if "Response" in entry and "Actions" in entry["Response"]:
                actions = entry["Response"]["Actions"]
                for action_value in actions.items():
                    if "target" in action_value:
                        target_values.append(action_value["target"])
        print(target_values)
    
    def ctam_discover_crashdump_cap(self):
        """
        :Description:				Get CollectDiagnosticDataActionInfo 

        :returns:				    Array of all URIs under GpuId ThermalMetrics
        """
        self.collectdiagnostic_uri_list = []
        self.logservice_ras_uri_list = self.ctam_get_collectdiagnostic_logservices_uris()
        for uri in self.logservice_ras_uri_list:
            self.ctam_redfish_uri_deep_hunt(URI=uri, uri_hunt="LogService.CollectDiagnosticData", uri_listing = self.collectdiagnostic_uri_list, uri_analyzed=[], action=1)
        self.write_test_info("{}".format(self.collectdiagnostic_uri_list))
        return self.collectdiagnostic_uri_list
    
    def ctam_get_collectdiagnostic_logservices_uris(self):
        self.collectdiagnostic_logservices_uri_list=[]
        self.ctam_redfish_uri_deep_hunt("/redfish/v1/Managers", "LogServices", self.collectdiagnostic_logservices_uri_list, uri_analyzed=[])
        self.ctam_redfish_uri_deep_hunt("/redfish/v1/Systems", "LogServices", self.collectdiagnostic_logservices_uri_list, uri_analyzed=[])
        self.write_test_info("{}".format(self.collectdiagnostic_logservices_uri_list))
        return self.collectdiagnostic_logservices_uri_list
            
