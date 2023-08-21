"""
Copyright (c) Microsoft Corporation

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

"""

from typing import Optional, List
from interfaces.functional_ifc import FunctionalIfc
import ast
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
    
    # def ctam_chassis_instance(self):
    #     URI = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/Chassis", component_type="GPU")
    #     response = self.dut().redfish_ifc.get(URI)
    #     JSONData = response.dict
    #     chassis_instances = [data["@odata.id"] for data in JSONData["Members"]]
    #     return chassis_instances
    
    def ctam_get_chassis_environment_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/EnvironmentMetrics

        :returns:				    Array of all URIs under EnvironmentMetrics
        """
        MyName = __name__ + "." + self.ctam_get_chassis_environment_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/EnvironmentMetrics"
            chassis_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(chassis_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_gpu_chassis_thermal_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Array of all URIs under ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_gpu_chassis_thermal_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/ThermalSubsystem/ThermalMetrics"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    # def ctam_baseboard_gpu_processor_instance(self): # return /redfish/v1/Systems/{BaseboardId} it will give baseboard id
    #     URI = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/Systems", component_type="GPU")
    #     response = self.dut().redfish_ifc.get(URI)
    #     JSONData = response.dict
    #     chassis_instances = [data["@odata.id"] for data in JSONData["Members"]]
    #     return chassis_instances
    
    # def ctam_gpu_thermal_instance(self): #return /redfish/v1/Chassis/{GpuId} it will give gpu id
    #     chassis_instances = self.ctam_baseboard_gpu_processor_instance()
    #     response_list = []
    #     for uri in chassis_instances:
    #         uri = uri + "/Processors"
    #         URI = self.dut().uri_builder.format_uri(redfish_str='{BaseURI}'+ uri, component_type="GPU") #/redfish/v1/Systems/{Baseboardid}/Processors
    #         response = self.dut().redfish_ifc.get(URI)
    #         response_list.append(response.dict)
    #     return response_list

    # def ctam_gpu_thermal_id(self):
    #     """
    #     :returns:                   Only returns GpuId
    #     """     
    #     gpu_thermal_instance = self.ctam_gpu_thermal_instance()
    #     members = []
    #     for gpu in gpu_thermal_instance:
    #         members.extend([data["@odata.id"] for data in gpu["Members"]])
    #     gpu_id = []
    #     for gpu in members:
    #         value = gpu.split('/')[-1]
    #         gpu_id.append(value)
    #     return gpu_id


    def ctam_gpu_thermal_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{GpuId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Array of all URIs under GpuId ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_gpu_thermal_metrics.__qualname__
        gpu_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisGPUs}", component_type="GPU"))
        print(gpu_instances)
        result = True
        for gpu_id in gpu_instances:
            uri = "/Chassis/" + gpu_id + "/ThermalSubsystem/ThermalMetrics"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_baseboard_gpu_processor_metrics(self): #need improvement
        """
        :Description:				Read back the data of /redfish/v1/Systems/{BaseboardId}/Processors/{GpuId}/ProcessorMetrics

        :returns:				    Array of all URIs under ProcessorMetrics
        """
        MyName = __name__ + "." + self.ctam_baseboard_gpu_processor_metrics.__qualname__
        system_gpu_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{SystemGPUs}", component_type="GPU"))
        baseboard_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
        result = True
        for id in baseboard_id:
            for gpu_id in system_gpu_id:
                uri = "/Systems/" + id + "/Processors/" + gpu_id + "/ProcessorMetrics"
                gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
                response = self.dut().redfish_ifc.get(gpu_uri)
                JSONData = response.dict
                status = response.status
                if status == 200 or status == 201:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                    result = False
        return result
    
    def ctam_get_all_metric_reports(self):
        mr_uri_list = self.ctam_get_all_metric_reports_uri()
        mr_json = {}
        for URI in mr_uri_list:
            response = self.dut().redfish_ifc.get("{}{}".format(self.dut().uri_builder.format_uri(redfish_str="{GPUMC}", component_type="GPU"), URI))
            JSONData = response.dict
            for metric_property in JSONData["MetricValues"]:
                mr_json[metric_property["MetricProperty"]] = metric_property["MetricValue"]
        return mr_json
    
    def ctam_chassis_assembly_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/Assembly

        """
        MyName = __name__ + "." + self.ctam_chassis_assembly_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        # assembly_keys = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{AssemblyInfo}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/Assembly"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_chassis_ids_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}

        """
        MyName = __name__ + "." + self.ctam_chassis_ids_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_chassis_power_subsystem_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/PowerSubsystem

        """
        MyName = __name__ + "." + self.ctam_chassis_power_subsystem_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/PowerSubsystem"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    def ctam_chassis_sensors_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/Sensors

        """
        MyName = __name__ + "." + self.ctam_chassis_sensors_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/Sensors"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    def ctam_chassis_sensor_ids_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/Sensors/{SensorId}

        """
        MyName = __name__ + "." + self.ctam_chassis_sensor_ids_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        sensor_ids = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{SensorIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            for ids in sensor_ids:
                URI = "/Chassis/" + uri + "/Sensors/" + ids
                gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
                response = self.dut().redfish_ifc.get(gpu_uri)
                JSONData = response.dict
                print(JSONData)
                status = response.status
                print(status)
                if status == 200 or status == 201:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                    result = False
        return result

    def ctam_chassis_thermal_subsystem_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/ThermalSubsystem

        """
        MyName = __name__ + "." + self.ctam_chassis_thermal_subsystem_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/ThermalSubsystem"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().redfish_ifc.get(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result