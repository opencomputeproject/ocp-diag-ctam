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

class TelemetryIfc(FunctionalIfc):

    _instance: Optional["TelemetryIfc"] = None

    def __new__(cls, *args, **kwargs):
        """
        ensure only 1 instance can be created

        :return: instance
        :rtype: TelemetryIfc
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
        :rtype: TelemetryIfc
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
    
    def ctam_get_chassis_environment_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/EnvironmentMetrics

        :returns:				    Array of all URIs under EnvironmentMetrics
        """
        MyName = __name__ + "." + self.ctam_get_chassis_environment_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        # reference_uri = r"/redfish/v1/Chassis/{ChassisId}/EnvironmentMetrics"
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/EnvironmentMetrics"
            base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
            chassis_uri = base_uri + uri
            response = self.dut().run_redfish_command(uri=chassis_uri)
            JSONData = response.dict
            # response_check = self.dut().check_uri_response(reference_uri, JSONData)
            # msg = "Checking for redfish uri for Accelerator Compliance, Result : {}".format( response_check)            
            # self.write_test_info(msg)
            status = response.status
            if (status == 200 or status == 201):
                self.test_run().add_log(LogSeverity.INFO, "Test JSON")
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, json.dumps(JSONData, indent=4)))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_gpu_chassis_thermal_metrics(self, path=None):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Array of all URIs under ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_gpu_chassis_thermal_metrics.__qualname__
        if path is None:
            chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        elif path == "Retimers":
            chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisRetimersIDs}", component_type="GPU"))            

        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/ThermalSubsystem/ThermalMetrics"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(uri=gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    def ctam_gpu_thermal_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{GpuId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Array of all URIs under GpuId ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_gpu_thermal_metrics.__qualname__
        gpu_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisGPUs}", component_type="GPU"))
        result = True
        for gpu_id in gpu_instances:
            uri = "/Chassis/" + gpu_id + "/ThermalSubsystem/ThermalMetrics"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(uri=gpu_uri)
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
        system_gpu_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{SystemGPUIDs}", component_type="GPU"))
        baseboard_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
        result = True
        for id in baseboard_id:
            for gpu_id in system_gpu_id:
                uri = "/Systems/" + id + "/Processors/" + gpu_id + "/ProcessorMetrics"
                gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
                response = self.dut().run_redfish_command(uri=gpu_uri)
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

    def ctam_chassis_ids_metrics(self, path=None):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}

        """
        MyName = __name__ + "." + self.ctam_chassis_ids_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            if path is None:
                uri = "/Chassis/" + uri
            else:
                uri = "/Chassis/" + uri + "/" + path
            
            chassis_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(chassis_uri)
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
            chassis_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(chassis_uri)
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
            sensor_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(sensor_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    '''def ctam_chassis_sensor_ids_metrics(self):
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
                sensor_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
                response = self.dut().run_redfish_command(sensor_uri)
                JSONData = response.dict
                status = response.status
                if status == 200 or status == 201:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                    result = False
        return result'''

    def ctam_chassis_thermal_subsystem_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisId}/ThermalSubsystem

        """
        MyName = __name__ + "." + self.ctam_chassis_thermal_subsystem_metrics.__qualname__
        chassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))
        result = True
        for uri in chassis_instances:
            uri = "/Chassis/" + uri + "/ThermalSubsystem"
            chassis_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(chassis_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    def ctam_systems_baseboard_ids(self, path=""):
        """
        :Description:				Read back the data of /redfish/v1/Systems/{BaseboardId}

        """
        MyName = __name__ + "." + self.ctam_systems_baseboard_ids.__qualname__
        systems_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
        result = True
        for uri in systems_instances:
            uri = "/Systems/" + uri + "/" + path
            baseboard_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + uri, component_type="GPU")
            response = self.dut().run_redfish_command(baseboard_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
    
    def ctam_systems_gpu_ids(self, path=""):
        """
        :Description:				Read back the data of /redfish/v1/Systems/{BaseboardId}/Processors/{GpuId}

        """
        MyName = __name__ + "." + self.ctam_systems_gpu_ids.__qualname__
        systems_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
        gpu_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{SystemGPUIDs}", component_type="GPU"))
        result = True
        for uri in systems_instances:
            for id in gpu_id:
                URI = "/Systems/" + uri + "/Processors/" + id + "/" + path
                gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
                response = self.dut().run_redfish_command(gpu_uri)
                JSONData = response.dict
                status = response.status
                if status == 200 or status == 201:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                    result = False
        return result
    
    def ctam_system_gpu_port_ids(self, path=""): # Need improvement
        """
        :Description:				Read back the data of /redfish/v1/Systems/{BaseboardId}/Processors/{GpuId}/Ports/{PortId}

        """
        MyName = __name__ + "." + self.ctam_system_gpu_port_ids.__qualname__
        systems_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
        gpu_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{SystemGPUIDs}", component_type="GPU"))
        port_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{SystemGPUPortIDs}", component_type="GPU"))
        result = True
        for uri in systems_instances:
            for id in gpu_id:
                for port in port_id:
                    URI = "/Systems/" + uri + "/Processors/" + id + "/Ports/" + port + path
                    gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
                    response = self.dut().run_redfish_command(gpu_uri)
                    JSONData = response.dict
                    status = response.status
                    if status == 200 or status == 201:
                        self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
                    else:
                        self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                        result = False
        return result
    
    def ctam_system_gpu_dram_ids(self, path=""):
        """
        :Description:				Read back the data of /redfish/v1/Systems/{BaseboardId}/Memory/{GpuDramId}

        """
        MyName = __name__ + "." + self.ctam_system_gpu_dram_ids.__qualname__
        systems_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{BaseboardIDs}", component_type="GPU"))
        gpu_dram_id = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{GPUDramIDs}", component_type="GPU"))
        
        result = True
        for uri in systems_instances:
            for id in gpu_dram_id:
                URI = "/Systems/" + uri + "/Memory/" + id + "/" + path
                gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
                response = self.dut().run_redfish_command(gpu_uri)
                JSONData = response.dict
                status = response.status
                if status == 200 or status == 201:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                    result = False
        return result
    
    def ctam_managers_read(self):
        """
        :Description:				Read back the data of redfish/v1/Managers/{mgr_instance}

        """
        MyName = __name__ + "." + self.ctam_managers_read.__qualname__
        mgr_instance = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ManagerIDs}", component_type="GPU"))
        result = True
        for uri in mgr_instance:
            URI = "/Managers/" + uri
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
            payload = {"DateTime": "2023-08-22T05:17:24+00:00"}
            head = {"Content-Type: application/json"}
            response = self.dut().run_redfish_command(gpu_uri, body=payload, headers=head)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                result = False
        return result
    
    def ctam_managers_ethernet_interfaces_usb0(self):
        """
        :Description:				Read back the data of redfish/v1/Managers/{mgr_instance}/EthernetInterfaces/usb0

        """
        MyName = __name__ + "." + self.ctam_managers_ethernet_interfaces_usb0.__qualname__
        mgr_instance = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ManagerIDs}", component_type="GPU"))
        result = True
        for uri in mgr_instance:
            URI = "/Managers/" + uri + "/EthernetInterfaces/usb0"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
            # payload = {"IPv4StaticAddresses": [{"Address": "192.168.31.1", "AddressOrigin": "Static", "Gateway":"192.168.31.2", "SubnetMask": "255.255.0.0"}]}
            # head = {"Content-Type: application/json"}
            # response = self.dut().run_redfish_command(gpu_uri, body=payload, headers=head)
            response = self.dut().run_redfish_command(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                result = False
        return result
    
    def ctam_managers_ethernet_interfaces_gateway(self): # need improvement
        """
        :Description:				Read back the data of redfish/v1/Managers/{mgr_instance}/EthernetInterfaces/usb0/Gateway property

        """
        MyName = __name__ + "." + self.ctam_managers_ethernet_interfaces_gateway.__qualname__
        mgr_instance = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ManagerIDs}", component_type="GPU"))
        result = True
        for uri in mgr_instance:
            URI = "/Managers/" + uri + "/EthernetInterfaces/usb0"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
            response = self.dut().run_redfish_command(gpu_uri)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                if "IPv4StaticAddresses" in JSONData:
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, JSONData))
                    result = False
        return result
    
    def ctam_managers_ethernet_interfaces_gateway_write(self):
        """
        :Description:				Read back the data of redfish/v1/Managers/{mgr_instance}/EthernetInterfaces/usb0/Gateway property

        """
        MyName = __name__ + "." + self.ctam_managers_ethernet_interfaces_gateway_write.__qualname__
        mgr_instance = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ManagerIDs}", component_type="GPU"))
        result = True
        for uri in mgr_instance:
            URI = "/Managers/" + uri + "/EthernetInterfaces/usb0"
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
            payload = {"IPv4StaticAddresses": [{"Address": "192.168.31.1", "Gateway":"192.168.31.2", "SubnetMask": "255.255.0.0"}]}
            header = {"Content-Type: application/json"}
            response = self.dut().run_redfish_command(gpu_uri, mode="PATCH", body=payload, headers=header)
            status = response.status
            if status == 204:
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(URI, status))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(URI, response))
                result = False
        return result

    # def ctam_baseboard_gpu_processor_instance(self): # return /redfish/v1/Systems/{BaseboardId} it will give baseboard id
    #     URI = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}/Systems", component_type="GPU")
    #     response = self.dut().run_redfish_command(URI)
    #     JSONData = response.dict
    #     chassis_instances = [data["@odata.id"] for data in JSONData["Members"]]
    #     return chassis_instances
    
    # def ctam_gpu_thermal_instance(self): #return /redfish/v1/Chassis/{GpuId} it will give gpu id
    #     chassis_instances = self.ctam_baseboard_gpu_processor_instance()
    #     response_list = []
    #     for uri in chassis_instances:
    #         uri = uri + "/Processors"
    #         URI = self.dut().uri_builder.format_uri(redfish_str='{BaseURI}'+ uri, component_type="GPU") #/redfish/v1/Systems/{Baseboardid}/Processors
    #         response = self.dut().run_redfish_command(URI)
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

    def ctam_managers_set_sel_time(self): # Probably need improvement
        """
        :Description:				Set sel time at redfish/v1/Managers/{mgr_instance} property

        """
        MyName = __name__ + "." + self.ctam_managers_set_sel_time.__qualname__
        mgr_instance = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ManagerIDs}", component_type="GPU"))
        result = True
        for uri in mgr_instance:

            URI = "/Managers/" + uri
            gpu_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}" + URI, component_type="GPU")
            response = self.dut().run_redfish_command(uri=gpu_uri)
            JSONData = response.dict
            JSONData_DateTime = JSONData["DateTime"]
            status = response.status
            if status == 200 or status == 201:
                self.test_run().add_log(LogSeverity.INFO, "Getting Date time from Manager with ID Pass: {} : {}".format(uri, JSONData_DateTime))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Getting Date time from Manager ID Fails: {} : {}".format(uri, JSONData_DateTime))
                result = False
                break

            payload = {"DateTime": JSONData_DateTime}
            header = {"Content-Type: application/json"}
            response = self.dut().run_redfish_command(gpu_uri, mode="PATCH", body=payload, headers=header)
            JSONData = response.dict
            status = response.status
            if status == 200 or status == 201:
                if "DateTime" in JSONData:
                    self.test_run().add_log(LogSeverity.INFO, "Setting Sel Time ID Pass: {} : {}".format(URI, JSONData))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Setting Sel Time ID Fails: {} : {}".format(URI, JSONData))
                    result = False
        return result

    def ctam_get_chassis_fpga_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisFpgaIDs}

        :returns:				    Dictionary record under of all URIs under /redfish/v1/Chassis/{ChassisFpgaIDs}
        """
        MyName = __name__ + "." + self.ctam_get_chassis_fpga_metrics.__qualname__
        systemchassis_instances = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisFpgaIDs}", component_type="GPU"))
        result = True
        # reference_uri = r"/redfish/v1/Chassis/{ChassisFpgaIDs}"
        for uri in systemchassis_instances:
            uri = "/Chassis/" + uri
            base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
            chassis_uri = base_uri + uri
            response = self.dut().run_redfish_command(uri=chassis_uri)
            JSONData = response.dict
            # response_check = self.dut().check_uri_response(reference_uri, JSONData)
            # msg = "Checking for redfish uri for Accelerator Compliance, Result : {}".format( response_check)            
            # self.write_test_info(msg)
            status = response.status
            if (status == 200 or status == 201):
                self.test_run().add_log(LogSeverity.INFO, "Test JSON")
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, json.dumps(JSONData, indent=4)))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}/nstatus is {}".format(uri, JSONData, status))
                result = False
        return result
    
    def ctam_get_chassis_fpga_sensor_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisFpgaIDs}/Sensors

        :returns:				    Dictionary record under of all URIs under /redfish/v1/Chassis/{ChassisFpgaIDs}/Sensors
        """
        MyName = __name__ + "." + self.ctam_get_chassis_fpga_sensor_metrics.__qualname__
        chassis_sensor_list = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisSensorID}", component_type="GPU"))
        chassis_fpga_list = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisFpgaIDs}", component_type="GPU"))
        result = True
        # reference_uri = r"/redfish/v1/Chassis/{ChassisFpgaIDs}/Sensors"
        for sensorInstance,fpgaInstance in product(chassis_sensor_list, chassis_fpga_list):
            uri = "/Chassis/" + fpgaInstance + "/Sensors/" + sensorInstance
            base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
            chassis_uri = base_uri + uri
            response = self.dut().run_redfish_command(uri=chassis_uri)
            JSONData = response.dict
            # response_check = self.dut().check_uri_response(reference_uri, JSONData)
            # msg = "Checking for redfish uri for Accelerator Compliance, Result : {}".format( response_check)            
            # self.write_test_info(msg)
            status = response.status
            if (status == 200 or status == 201):
                self.test_run().add_log(LogSeverity.INFO, "Test JSON")
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, json.dumps(JSONData, indent=4)))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_get_chassis_sensor_metrics(self, path="ChassisRetimersIDs"):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{path}/Sensors

        :returns:				    Dictionary record under of all URIs under /redfish/v1/Chassis/{path}/Sensors
        """
        MyName = __name__ + "." + self.ctam_get_chassis_sensor_metrics.__qualname__
        sensorNameList = []

        if path == "ChassisRetimersIDs":
            outer_list = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisRetimersIDs}", component_type="GPU"))
        elif path == "ChassisIDs":
            outer_list = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisIDs}", component_type="GPU"))

        # reference_uri = r"/redfish/v1/Chassis/{path}/Sensors"
        result = True

        for outler_list_instance in outer_list:
            uri = "/Chassis/" + outler_list_instance + "/Sensors"
            self.test_run().add_log(LogSeverity.INFO, "Outler Loop is {}".format(outler_list_instance))
            base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
            chassis_uri = base_uri + uri
            response = self.dut().run_redfish_command(uri=chassis_uri)
            JSONData = response.dict
            sensorMembers = JSONData["Members"]

            for sensorIdRecord in sensorMembers:
                sensorName = sensorIdRecord["@odata.id"].split('/')[-1].strip()
                #sensorNameList.append(sensorName)
                #for sensorInstance in sensorNameList:
                uri = "/Chassis/" + outler_list_instance + "/Sensors/" + sensorName
                base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
                chassis_uri = base_uri + uri
                response = self.dut().run_redfish_command(uri=chassis_uri)
                JSONData = response.dict
                # response_check = self.dut().check_uri_response(reference_uri, JSONData)
                # msg = "Checking for redfish uri for Accelerator Compliance, Result : {}".format( response_check)            
                # self.write_test_info(msg)
                status = response.status
                if (status == 200 or status == 201):
                    self.test_run().add_log(LogSeverity.INFO, "Test JSON")
                    self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, json.dumps(JSONData, indent=4)))
                else:
                    self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                    result = False
                    return result
        return result

    def ctam_get_chassis_retimers_ThermalSubsystem_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisRetimersIDs}/ThermalSubsystem

        :returns:				    Dictionary record under of all URIs under /redfish/v1/Chassis/{ChassisRetimersIDs}/ThermalSubsystem
        """
        MyName = __name__ + "." + self.ctam_get_chassis_retimers_ThermalSubsystem_metrics.__qualname__
        chassis_retimer_list = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisRetimersIDs}", component_type="GPU"))
        result = True
        # reference_uri = r"/redfish/v1/Chassis/{ChassisRetimersIDs}/ThermalSubsystem"
        for retimerInstance in chassis_retimer_list:
            uri = "/Chassis/" + retimerInstance + "/ThermalSubsystem/"
            base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
            chassis_uri = base_uri + uri
            response = self.dut().run_redfish_command(uri=chassis_uri)
            JSONData = response.dict
            # response_check = self.dut().check_uri_response(reference_uri, JSONData)
            # msg = "Checking for redfish uri for Accelerator Compliance, Result : {}".format( response_check)            
            # self.write_test_info(msg)
            status = response.status
            if (status == 200 or status == 201):
                self.test_run().add_log(LogSeverity.INFO, "Test JSON")
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, json.dumps(JSONData, indent=4)))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result

    def ctam_get_chassis_fpga_Thermal_metrics(self):
        """
        :Description:				Read back the data of /redfish/v1/Chassis/{ChassisFpgaId}/ThermalSubsystem/ThermalMetrics

        :returns:				    Dictionary record under of all URIs under /redfish/v1/Chassis/{ChassisFpgaId}/ThermalSubsystem/ThermalMetrics
        """
        MyName = __name__ + "." + self.ctam_get_chassis_fpga_Thermal_metrics.__qualname__
        chassis_list = ast.literal_eval(self.dut().uri_builder.format_uri(redfish_str="{ChassisFpgaIDs}", component_type="GPU"))
        result = True
        # reference_uri = r"/redfish/v1/Chassis/{ChassisFpgaId}/ThermalSubsystem/ThermalMetrics"
        for chassisItem in chassis_list:
            uri = "/Chassis/" + chassisItem + "/ThermalSubsystem/ThermalMetrics"
            base_uri = self.dut().uri_builder.format_uri(redfish_str="{BaseURI}", component_type="GPU")
            chassis_uri = base_uri + uri
            response = self.dut().run_redfish_command(uri=chassis_uri)
            JSONData = response.dict
            # response_check = self.dut().check_uri_response(reference_uri, JSONData)
            # msg = "Checking for redfish uri for Accelerator Compliance, Result : {}".format( response_check)            
            # self.write_test_info(msg)
            status = response.status
            if (status == 200 or status == 201):
                self.test_run().add_log(LogSeverity.INFO, "Test JSON")
                self.test_run().add_log(LogSeverity.INFO, "Chassis with ID Pass: {} : {}".format(uri, json.dumps(JSONData, indent=4)))
            else:
                self.test_run().add_log(LogSeverity.FATAL, "Chassis with ID Fails: {} : {}".format(uri, JSONData))
                result = False
        return result
