"""
Copyright (c) Microsoft Corporation

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

class TelemetryIfc(FunctionalIfc):

    _instance: Optional["TelemetryIfc"] = None

    def __new__(cls, *args, **kwargs):
        """
        ensure only 1 instance can be created

        :return: instance
        :rtype: FWUpdateIfc
        """
        if not isinstance(cls._instance, cls):
            cls._instance = super(TelemetryIfc, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self):
        super().__init__()

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
        response = self.dut().redfish_ifc.get("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
        JSONData = response.dict
        if member_hunt in JSONData:
            uri_listing.append(URI)
            return
        if "Members" in JSONData:
            i = 0
            for element in JSONData["Members"]:
                if "@odata.id" in element:
                    URI = JSONData["Members"][i]["@odata.id"]
                    print(URI)
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
            print(URI)
            self.ctam_redfish_hunt(URI, "MetricValues", MetricReports)
        return MetricReports
    
    def ctam_chassis_instance(self):
        URI = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/Chassis", component_type="GPU")
        response = self.dut().redfish_ifc.get(URI)
        JSONData = response.dict
        chassis_instances = [data["@odata.id"] for data in JSONData["Members"]]
        return chassis_instances
    
    def ctam_get_chassis_environment_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/EnvironmentMetrics

        :returns:				    Array of all URIs under Envo
        """
        MyName = __name__ + "." + self.ctam_get_chassis_environment_metrics.__qualname__
        chassis_instances = self.ctam_chassis_instance()
        result = True
        for uri in chassis_instances:
            uri = uri + "/EnvironmentMetrics"
            response = self.dut().redfish_ifc.get("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), uri))
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_gpu_chassis_thermal_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Array of all URIs under ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_gpu_chassis_thermal_metrics.__qualname__
        chassis_instances = self.ctam_chassis_instance()
        result = True
        for uri in chassis_instances:
            uri = uri + "/ThermalSubsystem/ThermalMetrics"
            response = self.dut().redfish_ifc.get("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), uri))
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    def ctam_baseboard_gpu_processor_instance(self): # return /redfish/v1/Systems/{BaseboardId} it will give baseboard id
        URI = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/Systems", component_type="GPU")
        response = self.dut().redfish_ifc.get(URI)
        JSONData = response.dict
        chassis_instances = [data["@odata.id"] for data in JSONData["Members"]]
        return chassis_instances
    
    def ctam_gpu_thermal_instance(self): #return /redfish/v1/Chassis/{GpuId} it will give gpu id
        chassis_instances = self.ctam_baseboard_gpu_processor_instance()
        response_list = []
        for uri in chassis_instances:
            uri = uri + "/Processors"
            URI = self.dut().uri_builder.format_uri(redfish_str='{GPUMC}'+ uri, component_type="GPU") #/redfish/v1/Systems/{Baseboardid}/Processors
            response = self.dut().redfish_ifc.get(URI)
            response_list.append(response.dict)
        return response_list

    def ctam_gpu_thermal_id(self):
        """
        :returns:                   Only returns GpuId
        """     
        gpu_thermal_instance = self.ctam_gpu_thermal_instance()
        members = []
        for gpu in gpu_thermal_instance:
            members.extend([data["@odata.id"] for data in gpu["Members"]])
        gpu_id = []
        for gpu in members:
            value = gpu.split('/')[-1]
            gpu_id.append(value)
        return gpu_id


    def ctam_gpu_thermal_metrics(self): #need improvement
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{GpuId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Array of all URIs under GpuId ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_gpu_thermal_metrics.__qualname__
        gpu_thermal_instances = self.ctam_gpu_thermal_id()
        result = True
        for gpu_id in gpu_thermal_instances:
            uri = "/Chassis/" + gpu_id + "/ThermalSubsystem/ThermalMetrics"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_baseboard_gpu_processor_metrics(self): #need improvement
        """
        :Description:				Read back the data of /redfish/v1/Systems/{BaseboardId}/Processors/{GpuId}/ProcessorMetrics

        :returns:				    Array of all URIs under ProcessorMetrics
        """
        MyName = __name__ + "." + self.ctam_baseboard_gpu_processor_metrics.__qualname__
        gpu_thermal_instances = self.ctam_gpu_thermal_id()
        base_id = self.ctam_baseboard_gpu_processor_instance()
        result = True
        for id in base_id:
            for gpu_id in gpu_thermal_instances:
                uri = id + "/Processors/" + gpu_id + "/ProcessorMetrics"
                baseboard_id = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
                response = self.dut().redfish_ifc.get(baseboard_id)
                JSONData = response.dict
                status = response.status
                if status == 200 or status == 201:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                    result = False
        return result