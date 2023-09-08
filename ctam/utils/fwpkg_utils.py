"""
Copyright (c) NVIDIA CORPORATION
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.

:Description:        This file holds all the useful firmware package manipulators. 

:Command line:       Library functions are made as generic as possible.

"""

import os
import shutil
import uuid
import math

class PLDMFwpkg:
    """
    Methods related to PLDM fwpkg in general
    """
    
    @staticmethod
    def corrupt_package_UUID(golden_fwpkg_path):
        """
        :Description:                       Corrupt the PackageHeaderIdentifier (UUID) of the .

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.write(bytearray(16)) # UUID is 16 bytes
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
            
        return corrupted_package_path

    @staticmethod
    def clear_component_metadata_in_pkg(golden_fwpkg_path, component_id=None, metadata_size=4096):
        """
        :Description:                       Clear metadata of any component in the PLDM bundle.
                                            If component_id is provided, corrupt the respective component's image.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int component_id:            ComponentIdentifier of the component image to be corrupted. Default is None.
        :param int metadata_size:           Metadata size in bytes. Default is 4096 bytes.

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        
        pldm_parser = PLDMUnpack()
        if result := pldm_parser.parse_pldm_package(corrupted_package_path):
            result = pldm_parser.corrupt_component_metadata_in_pkg(corrupted_package_path, component_id, metadata_size)
            
        if not result:
            print(f"Error in corrupting the package.")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
            
        return corrupted_package_path
    
    @staticmethod
    def clear_component_image_in_pkg(golden_fwpkg_path, component_id=None):
        """
        :Description:                       Clear image/payload of any component in the PLDM bundle.
                                            If component_id is provided, corrupt the respective component's image.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int component_id:            ComponentIdentifier of the component image to be corrupted. Default is None.

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        
        pldm_parser = PLDMUnpack()
        if result := pldm_parser.parse_pldm_package(corrupted_package_path):
            # Once unpacked, clear metadata of any component
            result = pldm_parser.clear_component_image_in_pkg(corrupted_package_path, component_id)
        if not result:
            print(f"Error in corrupting the package.")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
            
        return corrupted_package_path
    
    @staticmethod
    def make_large_package(golden_fwpkg_path, max_bundle_size):
        """
        :Description:                       Create a package that is larger than the allowed max size.

        :param str golden_fwpkg_path:	    Path to golden firmware package
        :param int max_bundle_size:         Maximum allowed size of the PLDM bundle.

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        
        with open(golden_fwpkg_path, 'rb') as infile:
            golden_fwpkg_content = infile.read()
        golden_fwpkg_size = os.path.getsize(golden_fwpkg_path)
        try:
            with open(corrupted_package_path, 'a+b') as large_fwpkg:
                for i in range(max_bundle_size//golden_fwpkg_size+1):
                    large_fwpkg.write(golden_fwpkg_content)
        except Exception as e:
            print(f"Error in creating a large package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None

        return corrupted_package_path

class FwpkgSignature:
    """
    Methods related to PLDM fwpkg signature
    """
    NUM_BYTES_FROM_END = 1024
    HeaderV2 = 2
    HeaderV3 = 3
    
    @staticmethod
    def get_major_minor_version_of_package_signature(package_path):
        """
        :Description:                       Get the major and minor version of the FW Update Package Signature Format.

        :param str fwpkg_path:      	    Path to firmware package
        
        :returns:                           The major and minor versions extracted from the package. (-1, -1) in case of failure.
        :rtype:                             Tuple[int, int]
        """
        try:
            with open(package_path, 'rb') as infile:
                infile.seek(-FwpkgSignature.NUM_BYTES_FROM_END, os.SEEK_END)
                infile.seek(4, 1)
                major_version = infile.read(1)
                minor_version = infile.read(1)

            return ord(major_version), ord(minor_version)
        except:
            return -1, -1

    @staticmethod
    def corrupt_single_byte_in_package_signature(fwpkg_path, skip_byte, value):
        """
        :Description:                       Corrupt a given single byte in the given FW package.

        :param str fwpkg_path:      	    Path to firmware package to be corrupted
        :param int skip_byte:               The offset of the byte to be corrupted from the start of signature header
        :param int value:                   The new value of the byte to be written

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        try:
            with open(fwpkg_path, 'r+b') as file:
                file.seek(-FwpkgSignature.NUM_BYTES_FROM_END + skip_byte, os.SEEK_END)
                file.write(bytes([value]))
            return True
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            return False
        
    @staticmethod
    def corrupt_signature_type_in_package(golden_fwpkg_path):
        """
        :Description:                       Corrupts the signature type in the FW package, 
                                            which is present at 14th byte from the start of signature header.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        major_package_version, _ = get_major_minor_version_of_package_signature(golden_fwpkg_path)
        if int(major_package_version) not in [FwpkgSignature.HeaderV2, FwpkgSignature.HeaderV3]:
            print(
                f"Package Major Version is not supported: {major_package_version}"
            )
            return None
        
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        
        if not corrupt_single_byte_in_package_signature(corrupted_package_path, 13, 255):
            print("Failed to corrupt the signature type")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
        return corrupted_package_path

    @staticmethod
    def invalidate_signature_in_pkg(golden_fwpkg_path):
        """
        :Description:                       Corrupts the magic number in the FW package, 
                                            which is present at 14th byte from the start of signature header.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.seek(-FwpkgSignature.NUM_BYTES_FROM_END, os.SEEK_END)
                file.write(bytearray(4)) # 4 bytes long Magic
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
        return corrupted_package_path

    @staticmethod
    def clear_signature_in_pkg(golden_fwpkg_path):
        """
        :Description:                       Clear the signature data appended at the end of
                                            the PLDM bundle.

        :param str golden_fwpkg_path:	    Path to golden firmware package

        :returns:                           Path to corrupted package. None if corruption fails. 
        :rtype:                             str
        """
        # Make a copy of the golden fwpkg
        corrupted_package =  os.path.join(os.path.dirname(golden_fwpkg_path), "corrupted-pkg.fwpkg")
        corrupted_package_path = shutil.copy(golden_fwpkg_path, corrupted_package)
        try:
            with open(corrupted_package_path, 'r+b') as file:
                file.seek(-FwpkgSignature.NUM_BYTES_FROM_END, os.SEEK_END)
                file.write(bytearray(FwpkgSignature.NUM_BYTES_FROM_END))
        except Exception as e:
            print(f"Error in corrupting the package: {e}")
            # delete the package
            os.remove(corrupted_package_path)
            corrupted_package_path = None
            
        return corrupted_package_path

class PLDMUnpack:
    """
    PLDMUnpack class implements a PLDM parser and the unpack tool
    along with its required features.
    """
    def __init__(self):
        """
        Contructor for PLDMUnpack class
        """
        self.unpack = True
        self.package = ""
        self.fwpkg_fd = 0
        self.header_map = {}
        self.device_id_record_count = 0
        self.fd_id_record_list = []
        self.component_img_info_list = []
        self.full_header = {
            "PackageHeaderInformation": {},
            "FirmwareDeviceIdentificationArea": {},
            "ComponentImageInformationArea": {},
            "Package Header Checksum": ''
        }
        self.verbose = False
        self.little_endian_list = [
            "IANA Enterprise ID", "PCI Vendor ID", "PCI Device ID",
            "PCI Subsystem Vendor ID", "PCI Subsystem ID"
        ]

    def parse_header(self):
        """
        :Description:                       Parse PLDM header data into self.header_map

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        # check if UUID is valid
        pldm_fw_header_id_v1_0 = b'\xf0\x18\x87\x8c\xcb\x7d\x49\x43\x98\x00\xa0\x2f\x05\x9a\xca\x02'
        uuid_v1_0 = str(uuid.UUID(bytes=pldm_fw_header_id_v1_0))
        self.header_map["PackageHeaderIdentifier"] = str(
            uuid.UUID(bytes=self.fwpkg_fd.read(16)))
        if uuid_v1_0 != self.header_map["PackageHeaderIdentifier"]:
            log_msg = "Expected PLDM v1.0 but PackageHeaderIdentifier is "\
            + self.header_map["PackageHeaderIdentifier"]
            print(log_msg)
            return False
        self.header_map["PackageHeaderFormatVersion"] = str(
            int.from_bytes(self.fwpkg_fd.read(1),
                           byteorder='little',
                           signed=False))
        self.header_map["PackageHeaderSize"] = int.from_bytes(
            self.fwpkg_fd.read(2), byteorder='little', signed=False)
        timestamp = self.fwpkg_fd.read(13)
        self.header_map["PackageReleaseDateTime"] = get_timestamp_str(
            timestamp)
        self.header_map["ComponentBitmapBitLength"] = int.from_bytes(
            self.fwpkg_fd.read(2), byteorder='little', signed=False)
        self.header_map["PackageVersionStringType"] = int.from_bytes(
            self.fwpkg_fd.read(1), byteorder='little', signed=False)
        version_str_len = int.from_bytes(self.fwpkg_fd.read(1),
                                         byteorder='little',
                                         signed=False)
        self.header_map["PackageVersionStringLength"] = version_str_len
        self.header_map["PackageVersionString"] = self.fwpkg_fd.read(
            version_str_len).decode('utf-8')
        self.full_header["PackageHeaderInformation"] = self.header_map
        return True

    def parse_device_id_records(self):
        """
        :Description:                       Parse PLDM FirmwareDeviceIDRecords data into self.fd_id_record_list

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        # pylint: disable=line-too-long
        self.device_id_record_count = int.from_bytes(self.fwpkg_fd.read(1),
                                                     byteorder='little',
                                                     signed=False)
        for _ in range(self.device_id_record_count):
            id_record_map = {}
            id_record_map["RecordLength"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            id_record_map["DescriptorCount"] = int.from_bytes(
                self.fwpkg_fd.read(1), byteorder='little', signed=False)
            id_record_map["DeviceUpdateOptionFlags"] = int.from_bytes(
                self.fwpkg_fd.read(4), byteorder='little', signed=False)
            id_record_map[
                "ComponentImageSetVersionStringType"] = int.from_bytes(
                    self.fwpkg_fd.read(1), byteorder='little', signed=False)
            id_record_map[
                "ComponentImageSetVersionStringLength"] = int.from_bytes(
                    self.fwpkg_fd.read(1), byteorder='little', signed=False)
            id_record_map["FirmwareDevicePackageDataLength"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            applicable_component_size = math.ceil(
                self.header_map["ComponentBitmapBitLength"] / 8)
            id_record_map["ApplicableComponents"] = int.from_bytes(
                self.fwpkg_fd.read(applicable_component_size),
                byteorder='little',
                signed=False)
            id_record_map[
                "ComponentImageSetVersionString"] = self.fwpkg_fd.read(
                    id_record_map["ComponentImageSetVersionStringLength"]
                ).decode('utf-8')
            descriptors = []
            for j in range(id_record_map["DescriptorCount"]):
                descriptor_map = {}
                if j == 0:
                    descriptor_map["InitialDescriptorType"] = int.from_bytes(
                        self.fwpkg_fd.read(2),
                        byteorder='little',
                        signed=False)
                    descriptor_map["InitialDescriptorLength"] = int.from_bytes(
                        self.fwpkg_fd.read(2),
                        byteorder='little',
                        signed=False)
                    value = self.fwpkg_fd.read(
                        descriptor_map["InitialDescriptorLength"])
                    descriptor_map["InitialDescriptorData"] = value

                else:
                    descriptor_map[
                        "AdditionalDescriptorType"] = int.from_bytes(
                            self.fwpkg_fd.read(2),
                            byteorder='little',
                            signed=False)
                    descriptor_map[
                        "AdditionalDescriptorLength"] = int.from_bytes(
                            self.fwpkg_fd.read(2),
                            byteorder='little',
                            signed=False)
                    if descriptor_map["AdditionalDescriptorType"] == 0xFFFF:
                        descriptor_map[
                            "VendorDefinedDescriptorTitleStringType"] = int.from_bytes(
                                self.fwpkg_fd.read(1),
                                byteorder='little',
                                signed=False)
                        descriptor_map[
                            "VendorDefinedDescriptorTitleStringLength"] = int.from_bytes(
                                self.fwpkg_fd.read(1),
                                byteorder='little',
                                signed=False)
                        descriptor_map[
                            "VendorDefinedDescriptorTitleString"] = self.fwpkg_fd.read(
                                descriptor_map[
                                    "VendorDefinedDescriptorTitleStringLength"]
                            ).decode('utf-8')
                        vendor_def_data_len = (
                            descriptor_map["AdditionalDescriptorLength"] -
                            (2 + descriptor_map[
                                "VendorDefinedDescriptorTitleStringLength"]))
                        descriptor_map[
                            "VendorDefinedDescriptorData"] = self.fwpkg_fd.read(
                                vendor_def_data_len).hex()
                    else:
                        descriptor_map[
                            "AdditionalDescriptorIdentifierData"] = self.fwpkg_fd.read(
                                descriptor_map["AdditionalDescriptorLength"])
                descriptors.append(descriptor_map)
            id_record_map["RecordDescriptors"] = descriptors
            id_record_map["FirmwareDevicePackageData"] = self.fwpkg_fd.read(
                id_record_map["FirmwareDevicePackageDataLength"]).decode(
                    'utf-8')
            self.fd_id_record_list.append(id_record_map)
        self.full_header["FirmwareDeviceIdentificationArea"] = {
            "DeviceIDRecordCount": self.device_id_record_count,
            "FirmwareDeviceIDRecords": self.fd_id_record_list
        }
        return True

    def parse_component_img_info(self):
        """
        :Description:                       Parse PLDM Component Image info data into self.fd_id_record_list

        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        component_image_count = int.from_bytes(self.fwpkg_fd.read(2),
                                               byteorder='little',
                                               signed=False)
        for _ in range(component_image_count):
            comp_info = {}
            comp_info["ComponentClassification"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            comp_info["ComponentIdentifier"] = hex(
                int.from_bytes(self.fwpkg_fd.read(2),
                               byteorder='little',
                               signed=False))
            comp_info["ComponentComparisonStamp"] = int.from_bytes(
                self.fwpkg_fd.read(4), byteorder='little', signed=False)
            comp_info["ComponentOptions"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            comp_info["RequestedComponentActivationMethod"] = int.from_bytes(
                self.fwpkg_fd.read(2), byteorder='little', signed=False)
            # RequestedComponentActivationMethod can have any combination of bits 0:5 set
            # Any value above 0x3F is invalid
            activation_val = comp_info["RequestedComponentActivationMethod"]
            if activation_val > 0x3F:
                Util.cli_log(
                    f"Found invalid value for RequestedComponentActivationMethod={activation_val}",
                    True)
            comp_info["ComponentLocationOffset"] = int.from_bytes(
                self.fwpkg_fd.read(4), byteorder='little', signed=False)
            comp_info["ComponentSize"] = int.from_bytes(self.fwpkg_fd.read(4),
                                                        byteorder='little',
                                                        signed=False)
            comp_info["ComponentVersionStringType"] = int.from_bytes(
                self.fwpkg_fd.read(1), byteorder='little', signed=False)
            comp_info["ComponentVersionStringLength"] = int.from_bytes(
                self.fwpkg_fd.read(1), byteorder='little', signed=False)
            comp_info["ComponentVersionString"] = self.fwpkg_fd.read(
                comp_info["ComponentVersionStringLength"]).decode('utf-8')
            self.component_img_info_list.append(comp_info)
        self.full_header["ComponentImageInformationArea"] = {
            "ComponentImageCount": component_image_count,
            "ComponentImageInformation": self.component_img_info_list
        }
        return True
    
    def get_pldm_header_checksum(self):
        """
        :Description:                       Read PLDM header checksum

        :returns:                           None
        :rtype:                             None
        """
        self.full_header['Package Header Checksum'] = int.from_bytes(
            self.fwpkg_fd.read(4), byteorder='little', signed=False)

    def parse_pldm_package(self, package_name):
        """
        :Description:                       Parse the PLDM package and get information about components included in the FW image.
        
        :param str package_name:	        Path to the firmware package to be parsed
        
        :returns:                           True if parsing successful
        :rtype:                             bool
        """
        if package_name == "" or package_name is None:
            log_msg = "ERROR: Firmware package file is mandatory."
            print(log_msg)
            return False
        if os.path.exists(package_name) is False:
            log_msg = print("ERROR: File does not exist at path ",
                            package_name)
            print(log_msg)
            return False
        self.package = package_name
        try:
            with open(self.package, "rb") as self.fwpkg_fd:
                parsing_valid = self.parse_header()
                if parsing_valid:
                    parsing_valid = self.parse_device_id_records()
                    if parsing_valid:
                        parsing_valid = self.parse_component_img_info()
                        self.get_pldm_header_checksum()
            return parsing_valid
        except IOError as e_io_error:
            log_message = f"Couldn't open or read given FW package ({e_io_error})"
            print(log_message)
            return False
        
    def corrupt_component_metadata_in_pkg(self, fwpkg_path, component_id=None, metadata_size=4096):
        """
        :Description:                       Corrupt a component's metadata in the given FW package.
                                            If component_id is provided, corrupt the respective component's image.
                                            Otherwise, corrupt the first component image in the package.
    
        :param str fwpkg_path:      	    Path to firmware package to be corrupted
        :param int component_id:            ComponentIdentifier (in hex format) of the component image to be corrupted. Default is None.
        :param int metadata_size:           Metadata size in bytes. Default is 4096 bytes.

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        corruption_status = False
        package_size = os.path.getsize(fwpkg_path)
        for index, info in enumerate(self.component_img_info_list):
            if component_id is not None and info["ComponentIdentifier"] != hex(int(component_id, 16)):
                continue
            # Lseek to the component from the PLDM fwpkg   
            offset = info["ComponentLocationOffset"]
            size = info["ComponentSize"]
            if offset + size > package_size:
                log_msg = f"Error: ComponentLocationOffset {offset} + \
                ComponentSize {size} exceeds given package size {package_size}"
                print(log_msg)
            print(f"Corrupting metadata of component: {self.component_img_info_list[index]}")
            try:
                with open(self.package, 'r+b') as self.fwpkg_fd:
                    self.fwpkg_fd.seek(offset)
                    # Zero out metadata bytes
                    # Save the bundle
                    self.fwpkg_fd.write(bytearray(metadata_size))
                    corruption_status = True
            except IOError as e_io_error:
                log_message = f"Couldn't open or read given FW package ({e_io_error})"
                print(log_message)
        return corruption_status
            
    def clear_component_image_in_pkg(self, fwpkg_path, component_id=None):
        """
        :Description:                       Clear a component's image/payload in the given FW package.
                                            If component_id is provided, corrupt the respective component's image.
                                            Otherwise, corrupt the first component image in the package.
    
        :param str fwpkg_path:      	    Path to firmware package to be corrupted
        :param int component_id:            ComponentIdentifier (in hex format) of the component image to be corrupted. Default is None.

        :returns:                           True if the corruption was successful, False otherwise.
        :rtype:                             bool
        """
        corruption_status = False
        package_size = os.path.getsize(fwpkg_path)
        for index, info in enumerate(self.component_img_info_list):
            if component_id is not None and info["ComponentIdentifier"] != hex(int(component_id, 16)):
                continue
            # Lseek to the component from the PLDM fwpkg   
            offset = info["ComponentLocationOffset"]
            size = info["ComponentSize"]
            if offset + size > package_size:
                log_msg = f"Error: ComponentLocationOffset {offset} + \
                ComponentSize {size} exceeds given package size {package_size}"
                print(log_msg)
            print(f"Corrupting component: {self.component_img_info_list[index]}")
            try:
                with open(self.package, 'r+b') as self.fwpkg_fd:
                    self.fwpkg_fd.seek(offset)
                    # Zero out and save the bundle
                    self.fwpkg_fd.write(bytearray(size))
                    corruption_status = True
            except IOError as e_io_error:
                log_message = f"Couldn't open or read given FW package ({e_io_error})"
                print(log_message)
        return corruption_status

def get_timestamp_str(timestamp):
    """
    :Description:                       Parse timestamp string from 13 byte binary data
                                        according to PLDM Base specification

    :param str timestamp:      	        Timestamp bytes to be parsed
    
    :returns:                           Timestamp in PLDM base spec format
    :rtype:                             str
    """
    year = timestamp[11]
    year = year << 8
    year = year | timestamp[10]
    time_str = str(year) + "-"
    time_str = time_str + str(timestamp[9])
    time_str = time_str + "-" + str(timestamp[8])
    time_str = time_str + " " + str(timestamp[7])
    time_str = time_str + ":" + str(timestamp[6])
    time_str = time_str + ":" + str(timestamp[5])
    micro_sec = timestamp[4]
    micro_sec = micro_sec << 8
    micro_sec = micro_sec | timestamp[3]
    micro_sec = micro_sec << 8
    micro_sec = micro_sec | timestamp[2]
    time_str = time_str + ":" + str(micro_sec)
    utc_offset = timestamp[1]
    utc_offset = utc_offset << 8
    utc_offset = utc_offset | timestamp[0]
    sign = "+"
    if utc_offset < 0:
        utc_offset = utc_offset * -1
        sign = "-"
    time_str = time_str + " " + sign + str(utc_offset)
    return time_str

