"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""

from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc
import ast
from datetime import datetime
from prettytable import PrettyTable
from ocptv.output import LogSeverity
from utils.json_utils import *
from itertools import product
try:
    from internal_interfaces.telemetry_ifc_int import TelemetryIfcInt as Meta
except:
    from utils.ctam_utils import MetaNull as Meta

class TelemetryIfc(FunctionalIfc, metaclass=Meta):

    # _instance: Optional["TelemetryIfc"] = None

    # def __new__(cls, *args, **kwargs):
    #     """
    #     ensure only 1 instance can be created

    #     :return: instance
    #     :rtype: TelemetryIfc
    #     """
    #     if not isinstance(cls._instance, cls):
    #         cls._instance = super(TelemetryIfc, cls).__new__(cls, *args, **kwargs)
    #     return cls._instance
    
    def __init__(self):
        super().__init__()

    # @classmethod
    # def get_instance(cls, *args, **kwargs):
    #     """
    #     if there is an existing instance, return it, otherwise create the singleton instance and return it

    #     :return: instance
    #     :rtype: TelemetryIfc
    #     """
    #     if not isinstance(cls._instance, cls):
    #         cls._instance = cls(*args, **kwargs)
    #     return cls._instance
    
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

    def ctam_get_all_metric_reports_uri(self):
        """
        :Description:				Function to build a list of all URIs that house a metric reports (MRs).
                                    Uses a recursive function to dig deep into Metric Report URIs which contain "MetricValues"

        :returns:				    Array of all URIs (type string)
        """
        MyName = __name__ + "." + self.ctam_get_all_metric_reports_uri.__qualname__
        JSONData = self.ctam_getts()
        if "MetricReports" in JSONData:
            MetricReports = []
            URI = JSONData["MetricReports"]["@odata.id"]
            self.ctam_redfish_hunt(URI, "MetricValues", MetricReports)
        return MetricReports
    
    # def ctam_chassis_instance(self):
    #     URI = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/Chassis", component_type="GPU")
    #     response = self.dut().run_redfish_command(URI)
    #     JSONData = response.dict
    #     chassis_instances = [data["@odata.id"] for data in JSONData["Members"]]
    #     return chassis_instances

    
    def ctam_get_all_metric_reports(self):
        mr_uri_list = self.ctam_get_all_metric_reports_uri()
        mr_json = {}
        for URI in mr_uri_list:
            response = self.dut().run_redfish_command(uri="{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
            JSONData = response.dict
            for metric_property in JSONData["MetricValues"]:
                mr_json[metric_property["MetricProperty"]] = metric_property["MetricValue"]
        if self.dut().is_console_log:
            t = PrettyTable(["MetricProperty", "MetricValue"])
            for k, v in mr_json.items():
                t.add_row([k, v])
            t.align["MetricProperty"] = "r"
            print(t)
        self.write_test_info("{}".format(mr_json))
        return mr_json

    