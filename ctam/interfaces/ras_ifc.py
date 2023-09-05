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
        :rtype: RasIfc
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
        :rtype: RasIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = cls(*args, **kwargs)
        return cls._instance
    
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
            
