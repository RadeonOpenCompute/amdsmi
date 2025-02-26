#!/usr/bin/env python3
#
# Copyright (C) Advanced Micro Devices. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import math
import os
import platform
import sys
import time
import re
import multiprocessing
import json

from enum import Enum
from typing import List, Set, Union

from amdsmi_init import *
from BDF import BDF


class AMDSMIHelpers():
    """Helper functions that aren't apart of the AMDSMI API
    Useful for determining platform and device identifiers

    Functions:
        os_info: tuple ()
    """

    def __init__(self) -> None:
        self.operating_system = platform.system()

        self._is_hypervisor = False
        self._is_virtual_os = False
        self._is_baremetal = False
        self._is_passthrough = False

        self._is_linux = False
        self._is_windows = False
        self._count_of_sets_called = 0

        # Check if the system is a virtual OS
        if self.operating_system.startswith("Linux"):
            self._is_linux = True
            logging.debug(f"AMDSMIHelpers: Platform is linux:{self._is_linux}")

            try:
                with open('/proc/cpuinfo', 'r') as f:
                    if 'hypervisor' in f.read():
                        self._is_virtual_os = True
            except IOError:
                pass

            self._is_baremetal = not self._is_virtual_os

        if self._is_virtual_os:
            #If hard coded passthrough device ids exist on Virtual OS,
            #   then it is a passthrough system
            output = self.get_pci_device_ids()
            passthrough_device_ids = ["7460", "73c8", "74a0", "74a1", "74a2"]
            if any(('0x' + device_id) in output for device_id in passthrough_device_ids):
                self._is_baremetal = True
                self._is_virtual_os = False
                self._is_passthrough = True

            # Check for passthrough system dynamically via drm querying id_flags
            try:
                if self.is_amdgpu_initialized() and not self._is_passthrough:
                    device_handles = amdsmi_interface.amdsmi_get_processor_handles()
                    for dev in device_handles:
                        virtualization_info = amdsmi_interface.amdsmi_get_gpu_virtualization_mode_info(dev)
                        if virtualization_info['mode'] == amdsmi_interface.AmdSmiVirtualizationMode.PASSTHROUGH:
                            self._is_baremetal = True
                            self._is_virtual_os = False
                            self._is_passthrough = True
                            break # Once passthrough is determined, we can immediately break
            except amdsmi_exception.AmdSmiLibraryException as e:
                logging.debug("Unable to determine virtualization status: " + e.get_error_code())

    def increment_set_count(self):
        self._count_of_sets_called += 1


    def get_set_count(self):
        return self._count_of_sets_called


    def is_virtual_os(self):
        return self._is_virtual_os


    def is_hypervisor(self):
        # Returns True if hypervisor is enabled on the system
        return self._is_hypervisor


    def is_baremetal(self):
        # Returns True if system is baremetal, if system is hypervisor this should return False
        return self._is_baremetal

    def is_passthrough(self):
        return self._is_passthrough


    def is_linux(self):
        return self._is_linux


    def is_windows(self):
        return self._is_windows


    def os_info(self, string_format=True):
        """Return operating_system and type information ex. (Linux, Baremetal)
        params:
            string_format (bool) True to return in string format, False to return Tuple
        returns:
            str or (str, str)
        """
        operating_system = ""
        if self.is_linux():
            operating_system = "Linux"
        elif self.is_windows():
            operating_system = "Windows"
        else:
            operating_system = "Unknown"

        operating_system_type = ""
        if self.is_baremetal():
            operating_system_type = "Baremetal"
        elif self.is_virtual_os():
            operating_system_type = "Guest"
        elif self.is_hypervisor():
            operating_system_type = "Hypervisor"
        else:
            operating_system_type = "Unknown"

        # Passthrough Override
        if self.is_passthrough():
            operating_system_type = "Guest (Passthrough)"

        if string_format:
            return f"{operating_system} {operating_system_type}"

        return (operating_system, operating_system_type)


    def get_amdsmi_init_flag(self):
        return AMDSMI_INIT_FLAG


    def is_amdgpu_initialized(self):
        return AMDSMI_INIT_FLAG & amdsmi_interface.amdsmi_wrapper.AMDSMI_INIT_AMD_GPUS


    def is_amd_hsmp_initialized(self):
        return AMDSMI_INIT_FLAG & amdsmi_interface.amdsmi_wrapper.AMDSMI_INIT_AMD_CPUS


    def get_rocm_version(self):
        try:
            rocm_lib_status, rocm_version = amdsmi_interface.amdsmi_get_rocm_version()
            if rocm_lib_status is not True:
                return "N/A"
            return rocm_version
        except amdsmi_interface.AmdSmiLibraryException as e:
            return "N/A"


    def get_cpu_choices(self):
        """Return dictionary of possible CPU choices and string of the output:
            Dictionary will be in format: cpus[ID]: Device Handle)
            String output will be in format:
                "ID: 0 "
        params:
            None
        return:
            (dict, str) : (cpu_choices, cpu_choices_str)
        """
        cpu_choices = {}
        cpu_choices_str = ""
        #import pdb;pdb.set_trace()
        try:
            cpu_handles = []
            # amdsmi_get_cpusocket_handles() returns the cpu socket handles stored for cpu_id
            cpu_handles = amdsmi_interface.amdsmi_get_cpusocket_handles()
        except amdsmi_interface.AmdSmiLibraryException as e:
            if e.err_code in (amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_NOT_INIT,
                              amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_DRIVER_NOT_LOADED):
                logging.info('Unable to get device choices, driver not initialized (amd_hsmp not found in modules)')
            else:
                raise e
        if len(cpu_handles) == 0:
            logging.info('Unable to find any devices, check if driver is initialized (amd_hsmp not found in modules)')
        else:
            # Handle spacing for the gpu_choices_str
            max_padding = int(math.log10(len(cpu_handles))) + 1

            for cpu_id, device_handle in enumerate(cpu_handles):
                cpu_choices[str(cpu_id)] = {
                        "Device Handle": device_handle
                }
                if cpu_id == 0:
                    id_padding = max_padding
                else:
                    id_padding = max_padding - int(math.log10(cpu_id))
                cpu_choices_str += f"ID: {cpu_id}\n"

            # Add the all option to the gpu_choices
            cpu_choices["all"] = "all"
            cpu_choices_str += f"  all{' ' * max_padding}| Selects all devices\n"

        return (cpu_choices, cpu_choices_str)

    def get_core_choices(self):
        """Return dictionary of possible Core choices and string of the output:
            Dictionary will be in format: coress[ID]: Device Handle)
            String output will be in format:
                "ID: 0 "
        params:
            None
        return:
            (dict, str) : (core_choices, core_choices_str)
        """
        core_choices = {}
        core_choices_str = ""

        try:
            core_handles = []
            # amdsmi_get_cpucore_handles() returns the core handles stored for core_id
            core_handles = amdsmi_interface.amdsmi_get_cpucore_handles()
        except amdsmi_interface.AmdSmiLibraryException as e:
            if e.err_code in (amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_NOT_INIT,
                              amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_DRIVER_NOT_LOADED):
                logging.info('Unable to get device choices, driver not initialized (amd_hsmp not found in modules)')
            else:
                raise e
        if len(core_handles) == 0:
            logging.info('Unable to find any devices, check if driver is initialized (amd_hsmp not found in modules)')
        else:
            # Handle spacing for the gpu_choices_str
            max_padding = int(math.log10(len(core_handles))) + 1

            for core_id, device_handle in enumerate(core_handles):
                core_choices[str(core_id)] = {
                        "Device Handle": device_handle
                }
                if core_id == 0:
                    id_padding = max_padding
                else:
                    id_padding = max_padding - int(math.log10(core_id))
            core_choices_str += f"ID: 0 - {len(core_handles) - 1}\n"

            # Add the all option to the core_choices
            core_choices["all"] = "all"
            core_choices_str += f"  all{' ' * max_padding}| Selects all devices\n"

        return (core_choices, core_choices_str)


    def get_output_format(self):
        """Returns the output format read from sys.argv
        Returns:
            str: outputformat
        """
        args = sys.argv[1:]
        outputformat = "human"
        if "--json" in args or "--j" in args:
            outputformat = "json"
        elif "--csv" in args or "--c" in args:
            outputformat = "csv"
        return outputformat


    def get_gpu_choices(self):
        """Return dictionary of possible GPU choices and string of the output:
            Dictionary will be in format: gpus[ID] : (BDF, UUID, Device Handle)
            String output will be in format:
                "ID: 0 | BDF: 0000:23:00.0 | UUID: ffffffff-0000-1000-0000-000000000000"
        params:
            None
        return:
            (dict, str) : (gpu_choices, gpu_choices_str)
        """
        gpu_choices = {}
        gpu_choices_str = ""
        device_handles = []

        try:
            # amdsmi_get_processor_handles returns the device_handles storted for gpu_id
            device_handles = amdsmi_interface.get_gpu_handles()
        except amdsmi_interface.AmdSmiLibraryException as e:
            if e.err_code in (amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_NOT_INIT,
                              amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_DRIVER_NOT_LOADED):
                logging.info('Unable to get device choices, driver not initialized (amdgpu not found in modules)')
            else:
                raise e

        if len(device_handles) == 0:
            logging.info('Unable to find any devices, check if driver is initialized (amdgpu not found in modules)')
        else:
            # Handle spacing for the gpu_choices_str
            max_padding = int(math.log10(len(device_handles))) + 1
            GPU_device=True
            for gpu_id, device_handle in enumerate(device_handles):
             device_type=amdsmi_interface.amdsmi_get_processor_type(device_handle)
             if device_type["processor_type"]=="AMDSMI_PROCESSOR_TYPE_AMD_GPU":
                bdf = amdsmi_interface.amdsmi_get_gpu_device_bdf(device_handle)
                uuid = amdsmi_interface.amdsmi_get_gpu_device_uuid(device_handle)
                gpu_choices[str(gpu_id)] = {
                    "BDF": bdf,
                    "UUID": uuid,
                    "Device Handle": device_handle,
                }

                if gpu_id == 0:
                    id_padding = max_padding
                else:
                    id_padding = max_padding - int(math.log10(gpu_id))
                gpu_choices_str += f"ID: {gpu_id}{' ' * id_padding}| BDF: {bdf} | UUID: {uuid}\n"

            # Add the all option to the gpu_choices
            gpu_choices["all"] = "all"
            gpu_choices_str += f"  all{' ' * max_padding}| Selects all devices\n"

        return (gpu_choices, gpu_choices_str)

    
    def get_nic_choices(self):
        nic_choices = {}
        nic_choices_str = ""
        device_handles = []

        try:
            # get_nic_handles returns the device_handles storted for nic_id
            device_handles = amdsmi_interface.get_nic_handles()
         
        except amdsmi_interface.AmdSmiLibraryException as e:
          
            if e.err_code in (amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_NOT_INIT,
                              amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_DRIVER_NOT_LOADED):
                logging.info('Unable to get device choices, driver not initialized (BRCM_NIC not found in modules)')
              
            else:
                raise e

        if len(device_handles) == 0:
            logging.info('Unable to find any devices, check if driver is initialized (BRCM_NIC not found in modules)')
        else:
            # Handle spacing for the gpu_choices_str
            max_padding = int(math.log10(len(device_handles))) + 1
          
            for nic_id, device_handle in enumerate(device_handles):
                bdf = amdsmi_interface.amdsmi_get_nic_device_bdf(device_handle)
              
                #uuid="abc"
                uuid = amdsmi_interface.amdsmi_get_nic_device_uuid(device_handle)
               
                nic_choices[str(nic_id)] = {
                    "BDF": bdf,
                    "UUID": uuid,
                    "Device Handle": device_handle,
                }

                if nic_id == 0:
                    id_padding = max_padding
                else:
                    id_padding = max_padding - int(math.log10(nic_id))
                nic_choices_str += f"ID: {nic_id}{' ' * id_padding}| BDF: {bdf} | UUID: {uuid}\n"

           
            # Add the all option to the gpu_choices
            nic_choices["all"] = "all"
            nic_choices_str += f"  all{' ' * max_padding}| Selects all devices\n"

        return (nic_choices, nic_choices_str)

     #BRCM POC to get switch choices 
    def get_switch_choices(self):
        switch_choices = {}
        switch_choices_str = ""
        device_handles = []

        try:
            # get_switch_handles returns the device_handles storted for switch_id
            device_handles = amdsmi_interface.get_switch_handles()
     
        except amdsmi_interface.AmdSmiLibraryException as e:
      
            if e.err_code in (amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_NOT_INIT,
                              amdsmi_interface.amdsmi_wrapper.AMDSMI_STATUS_DRIVER_NOT_LOADED):
                logging.info('Unable to get device choices, driver not initialized (BRCM_switch not found in modules)')
          
            else:
                raise e

        if len(device_handles) == 0:
            logging.info('Unable to find any devices, check if driver is initialized (BRCM_switch not found in modules)')
        else:
            # Handle spacing for the gpu_choices_str
            max_padding = int(math.log10(len(device_handles))) + 1
      
            for switch_id, device_handle in enumerate(device_handles):
                bdf = amdsmi_interface.amdsmi_get_switch_device_bdf(device_handle)
          
                #uuid="abc"
                uuid = amdsmi_interface.amdsmi_get_switch_device_uuid(device_handle)
           
                switch_choices[str(switch_id)] = {
                    "BDF": bdf,
                    "UUID": uuid,
                    "Device Handle": device_handle,
                }

                if switch_id == 0:
                    id_padding = max_padding
                else:
                    id_padding = max_padding - int(math.log10(switch_id))
                switch_choices_str += f"ID: {switch_id}{' ' * id_padding}| BDF: {bdf} | UUID: {uuid}\n"

       
            # Add the all option to the gpu_choices
            switch_choices["all"] = "all"
            switch_choices_str += f"  all{' ' * max_padding}| Selects all devices\n"

        return (switch_choices, switch_choices_str)

    @staticmethod
    def is_UUID(uuid_question: str) -> bool:
        """Determine if given string is of valid UUID format
        Args:
            uuid_question (str): the given string to be evaluated.
        Returns:
            True or False: wether the UUID given matches the UUID format.
        """
        UUID_pattern = re.compile("^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", flags=re.IGNORECASE)
        if re.match(UUID_pattern, uuid_question) is None:
            return False
        return True


    def get_device_handles_from_gpu_selections(self, gpu_selections: List[str], gpu_choices=None) -> tuple:
        """Convert provided gpu_selections to device_handles

        Args:
            gpu_selections (list[str]): Selected GPU ID(s), BDF(s), or UUID(s):
                    ex: ID:0  | BDF:0000:23:00.0 | UUID:ffffffff-0000-1000-0000-000000000000
            gpu_choices (dict{gpu_choices}): This is a dictionary of the possible gpu_choices
        Returns:
            (True, True, list[device_handles]): Returns a list of all the gpu_selections converted to
                amdsmi device_handles
            (False, valid_gpu_format, str): Return False, whether the format of the GPU input is valid, and the first input that failed to be converted
        """
        if 'all' in gpu_selections:
            return True, True, amdsmi_interface.amdsmi_get_processor_handles()

        if isinstance(gpu_selections, str):
            gpu_selections = [gpu_selections]

        if gpu_choices is None:
            # obtains dictionary of possible gpu choices
            gpu_choices = self.get_gpu_choices()[0]

        selected_device_handles = []
        for gpu_selection in gpu_selections:
            valid_gpu_choice = False

            for gpu_id, gpu_info in gpu_choices.items():
                bdf = gpu_info['BDF']
                is_bdf = True
                uuid = gpu_info['UUID']
                device_handle = gpu_info['Device Handle']

                # Check if passed gpu is a gpu ID or UUID
                if gpu_selection == gpu_id or gpu_selection.lower() == uuid:
                    selected_device_handles.append(device_handle)
                    valid_gpu_choice = True
                    break
                else:  # Check if gpu passed is a BDF object
                    try:
                        if BDF(gpu_selection) == BDF(bdf):
                            selected_device_handles.append(device_handle)
                            valid_gpu_choice = True
                            break
                    except Exception:
                        is_bdf = False
                        pass

            if not valid_gpu_choice:
                logging.debug(f"AMDSMIHelpers.get_device_handles_from_gpu_selections - Unable to convert {gpu_selection}")
                valid_gpu_format = True
                if not self.is_UUID(gpu_selection) and not gpu_selection.isdigit() and not is_bdf:
                    valid_gpu_format = False
                return False, valid_gpu_format, gpu_selection
        return True, True, selected_device_handles


    def get_device_handles_from_nic_selections(self, nic_selections: List[str], nic_choices=None):
    
        """Convert provided nic_selections to device_handles

        Args:
            nic_selections (list[str]): Selected NIC ID(s), BDF(s), or UUID(s):
                    ex: ID:0  | BDF:0000:23:00.0 | UUID:ffffffff-0000-1000-0000-000000000000
            nic_choices (dict{nic_choices}): This is a dictionary of the possible gpu_choices
        Returns:
            (True, list[device_handles]): Returns a list of all the nic_selections converted to
                amdsmi device_handles
            (False, str): Return False, and the first input that failed to be converted
        """
        if 'all' in nic_selections:
            return (True, amdsmi_interface.get_nic_handles())

        if isinstance(nic_selections, str):
            nic_selections = [nic_selections]
    
        if nic_choices is None:
            nic_choices = self.get_nic_choices()[0]

        selected_device_handles = []
        for nic_selection in nic_selections:
            valid_nic_choice = False

            for nic_id, nic_info in nic_choices.items():
                bdf = nic_info['BDF']
                uuid = nic_info['UUID']
                device_handle = nic_info['Device Handle']
            

                # Check if passed nic is a nic ID or UUID
                if nic_selection == nic_id or nic_selection.lower() == uuid:
                
                    device_type=amdsmi_interface.amdsmi_get_processor_type(device_handle)
                
                    selected_device_handles.append(device_handle)
                    valid_nic_choice = True
                    break
                else:  # Check if nic passed is a BDF object
                    try:
                        if BDF(nic_selection) == BDF(bdf):
                            selected_device_handles.append(device_handle)
                            valid_nic_choice = True
                            break
                    except Exception:
                        # Ignore exception when checking if the gpu_choice is a BDF
                        pass

            if not valid_nic_choice:
                logging.debug(f"AMDSMIHelpers.get_device_handles_from_gpu_selections - Unable to convert {nic_selection}")
            
                return False, nic_selection
            count=len(selected_device_handles)
        
        return True, selected_device_handles

    #BRCM POC to get device handles from switch selections
    def get_device_handles_from_switch_selections(self, switch_selections: List[str], switch_choices=None):

            """Convert provided switch_selections to device_handles

            Args:
                switch_selections (list[str]): Selected switch ID(s), BDF(s), or UUID(s):
                        ex: ID:0  | BDF:0000:23:00.0 | UUID:ffffffff-0000-1000-0000-000000000000
                switch_choices (dict{switch_choices}): This is a dictionary of the possible gpu_choices
            Returns:
                (True, list[device_handles]): Returns a list of all the switch_selections converted to
                    amdsmi device_handles
                (False, str): Return False, and the first input that failed to be converted
            """
            if 'all' in switch_selections:
                return (True, amdsmi_interface.get_switch_handles())

            if isinstance(switch_selections, str):
                switch_selections = [switch_selections]

            if switch_choices is None:
                switch_choices = self.get_switch_choices()[0]

            selected_device_handles = []
            for switch_selection in switch_selections:
                valid_switch_choice = False

                for switch_id, switch_info in switch_choices.items():
                    bdf = switch_info['BDF']
                    uuid = switch_info['UUID']
                    device_handle = switch_info['Device Handle']
        

                    # Check if passed switch is a switch ID or UUID
                    if switch_selection == switch_id or switch_selection.lower() == uuid:
            
                        device_type=amdsmi_interface.amdsmi_get_processor_type(device_handle)
            
                        selected_device_handles.append(device_handle)
                        valid_switch_choice = True
                        break
                    else:  # Check if switch passed is a BDF object
                        try:
                            if BDF(switch_selection) == BDF(bdf):
                                selected_device_handles.append(device_handle)
                                valid_switch_choice = True
                                break
                        except Exception:
                            # Ignore exception when checking if the gpu_choice is a BDF
                            pass

                if not valid_switch_choice:
                    logging.debug(f"AMDSMIHelpers.get_device_handles_from_gpu_selections - Unable to convert {switch_selection}")
        
                    return False, switch_selection
                count=len(selected_device_handles)
    
            return True, selected_device_handles    
    

    def get_device_handles_from_cpu_selections(self, cpu_selections: List[str], cpu_choices=None):
        """Convert provided cpu_selections to device_handles

        Args:
            cpu_selections (list[str]): Selected CPU ID(s):
                    ex: ID:0
            cpu_choices (dict{cpu_choices}): This is a dictionary of the possible cpu_choices
        Returns:
            (True, list[device_handles]): Returns a list of all the cpu_selections converted to
                amdsmi device_handles
            (False, str): Return False, and the first input that failed to be converted
        """
        if 'all' in cpu_selections:
            return True, True, amdsmi_interface.amdsmi_get_cpusocket_handles()

        if isinstance(cpu_selections, str):
            cpu_selections = [cpu_selections]

        if cpu_choices is None:
            cpu_choices = self.get_cpu_choices()[0]

        selected_device_handles = []
        for cpu_selection in cpu_selections:
            valid_cpu_choice = False
            for cpu_id, cpu_info in cpu_choices.items():
                device_handle = cpu_info['Device Handle']

                # Check if passed gpu is a gpu ID
                if cpu_selection == cpu_id:
                    selected_device_handles.append(device_handle)
                    valid_cpu_choice = True
                    break
            if not valid_cpu_choice:
                logging.debug(f"AMDSMIHelpers.get_device_handles_from_cpu_selections - Unable to convert {cpu_selection}")
                valid_cpu_format = True
                if not cpu_selection.isdigit():
                    valid_cpu_format = False
                return False, valid_cpu_format, cpu_selection
        return True, True, selected_device_handles


    def get_device_handles_from_core_selections(self, core_selections: List[str], core_choices=None):
        """Convert provided core_selections to device_handles

        Args:
            core_selections (list[str]): Selected CORE ID(s):
                    ex: ID:0
            core_choices (dict{core_choices}): This is a dictionary of the possible core_choices
        Returns:
            (True, list[device_handles]): Returns a list of all the core_selections converted to
                amdsmi device_handles
            (False, str): Return False, and the first input that failed to be converted
        """
        if 'all' in core_selections:
            return True, True, amdsmi_interface.amdsmi_get_cpucore_handles()

        if isinstance(core_selections, str):
            core_selections = [core_selections]

        if core_choices is None:
            core_choices = self.get_core_choices()[0]

        selected_device_handles = []
        for core_selection in core_selections:
            valid_core_choice = False
            for core_id, core_info in core_choices.items():
                device_handle = core_info['Device Handle']

                # Check if passed core is a core ID
                if core_selection == core_id:
                    selected_device_handles.append(device_handle)
                    valid_core_choice = True
                    break
            if not valid_core_choice:
                logging.debug(f"AMDSMIHelpers.get_device_handles_from_core_selections - Unable to convert {core_selection}")
                valid_core_format = True
                if not core_selection.isdigit():
                    valid_core_format = False
                return False, valid_core_format, core_selection
        return True, True, selected_device_handles


    def handle_gpus(self, args, logger, subcommand):
        """This function will run execute the subcommands based on the number
            of gpus passed in via args.
        params:
            args - argparser args to pass to subcommand
            current_platform_args (list) - GPU supported platform arguments
            current_platform_values (list) - GPU supported values for the arguments
            logger (AMDSMILogger) - Logger to print out output
            subcommand (AMDSMICommands) - Function that can handle multiple gpus

        return:
            tuple(bool, device_handle) :
                bool - True if executed subcommand for multiple devices
                device_handle - Return the device_handle if the list of devices is a length of 1
            (handled_multiple_gpus, device_handle)

        """
        if isinstance(args.gpu, list):
            if len(args.gpu) > 1:
                for device_handle in args.gpu:
                    device_type=amdsmi_interface.amdsmi_get_processor_type(device_handle)
                    if device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_AMD_GPU':
                        subcommand(args, multiple_devices=True, gpu=device_handle)
                    elif device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_BRCM_NIC':
                        subcommand(args, multiple_devices=True, nic=device_handle)
                    elif device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_BRCM_SWITCH':
                        subcommand(args, multiple_devices=True, switch=device_handle)     
                logger.print_output(multiple_device_enabled=True)
                return True, args.gpu
            elif len(args.gpu) == 1:
                args.gpu = args.gpu[0]
                return False, args.gpu
            else:
                logging.debug("args.gpu has an empty list")
        else:
            return False, args.gpu


    def handle_switchs(self, args, logger, subcommand):
    
        """This function will run execute the subcommands based on the number
            of gpus passed in via args.
        params:
            args - argparser args to pass to subcommand
            current_platform_args (list) - GPU supported platform arguments
            current_platform_values (list) - GPU supported values for the arguments
            logger (AMDSMILogger) - Logger to print out output
            subcommand (AMDSMICommands) - Function that can handle multiple gpus

        return:
            tuple(bool, device_handle) :
                bool - True if executed subcommand for multiple devices
                device_handle - Return the device_handle if the list of devices is a length of 1
            (handled_multiple_gpus, device_handle)

        """
    
        if isinstance(args.switch, list):
        
            if len(args.switch) > 1:
                for device_handle in args.switch:
                    device_type=amdsmi_interface.amdsmi_get_processor_type(device_handle)
                    if device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_AMD_GPU':
                        subcommand(args, multiple_devices=True, gpu=device_handle)
                    elif device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_BRCM_NIC':
                        subcommand(args, multiple_devices=True, nic=device_handle)
                    elif device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_BRCM_SWITCH':
                        subcommand(args, multiple_devices=True, switch=device_handle)      
                
                logger.print_output(multiple_device_enabled=True)
                return True, args.switch
            elif len(args.switch) == 1:
                args.switch = args.switch[0]
                return False, args.switch
            else:
                logging.debug("args.gpu has an empty list")
        else:
            return False, args.switch

    #BRCM POC to handle nics  
    def handle_nics(self, args, logger, subcommand):
    
        """This function will run execute the subcommands based on the number
            of nics passed in via args.
        params:
            args - argparser args to pass to subcommand
            current_platform_args (list) - nic supported platform arguments
            current_platform_values (list) - nic supported values for the arguments
            logger (AMDSMILogger) - Logger to print out output
            subcommand (AMDSMICommands) - Function that can handle multiple nics

        return:
            tuple(bool, device_handle) :
                bool - True if executed subcommand for multiple devices
                device_handle - Return the device_handle if the list of devices is a length of 1
            (handled_multiple_gpus, device_handle)

        """
    
        if isinstance(args.nic, list):
            
            if len(args.nic) > 1:
        
                for device_handle in args.nic:
                
                    device_type=amdsmi_interface.amdsmi_get_processor_type(device_handle)
                    if device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_AMD_GPU':
                        subcommand(args, multiple_devices=True, gpu=device_handle)

                    elif device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_BRCM_NIC':
                    
                        subcommand(args, multiple_devices=True, nic=device_handle)
                    elif device_type["processor_type"]=='AMDSMI_PROCESSOR_TYPE_BRCM_SWITCH':
                    
                        subcommand(args, multiple_devices=True, switch=device_handle) 
                        
                logger.print_output(multiple_device_enabled=True)
                return True, args.nic
            elif len(args.nic) == 1:
                args.nic = args.nic[0]
                return False, args.nic
            else:
                logging.debug("args.gpu has an empty list")
        else:
            return False, args.nic


    def handle_cpus(self, args, logger, subcommand):
        """This function will run execute the subcommands based on the number
            of cpus passed in via args.
        params:
            args - argparser args to pass to subcommand
            logger (AMDSMILogger) - Logger to print out output
            subcommand (AMDSMICommands) - Function that can handle multiple gpus

        return:
            tuple(bool, device_handle) :
                bool - True if executed subcommand for multiple devices
                device_handle - Return the device_handle if the list of devices is a length of 1
            (handled_multiple_gpus, device_handle)

        """
        if isinstance(args.cpu, list):
            if len(args.cpu) > 1:
                for device_handle in args.cpu:
                    # Handle multiple_devices to print all output at once
                    subcommand(args, multiple_devices=True, cpu=device_handle)
                logger.print_output(multiple_device_enabled=True)
                return True, args.cpu
            elif len(args.cpu) == 1:
                args.cpu = args.cpu[0]
                return False, args.cpu
            else:
                logging.debug("args.cpu has empty list")
        else:
            return False, args.cpu


    def handle_cores(self, args, logger, subcommand):
        """This function will run execute the subcommands based on the number
            of cores passed in via args.
        params:
            args - argparser args to pass to subcommand
            logger (AMDSMILogger) - Logger to print out output
            subcommand (AMDSMICommands) - Function that can handle multiple gpus

        return:
            tuple(bool, device_handle) :
                bool - True if executed subcommand for multiple devices
                device_handle - Return the device_handle if the list of devices is a length of 1
            (handled_multiple_gpus, device_handle)

        """
        if isinstance(args.core, list):
            if len(args.core) > 1:
                for device_handle in args.core:
                    # Handle multiple_devices to print all output at once
                    subcommand(args, multiple_devices=True, core=device_handle)
                logger.print_output(multiple_device_enabled=True)
                return True, args.core
            elif len(args.core) == 1:
                args.core = args.core[0]
                return False, args.core
            else:
                logging.debug("args.core has empty list")
        else:
            return False, args.core


    def handle_watch(self, args, subcommand, logger):
        """This function will run the subcommand multiple times based
            on the passed watch, watch_time, and iterations passed in.
        params:
            args - argparser args to pass to subcommand
            subcommand (AMDSMICommands) - Function that can handle
                watching output (Currently: metric & process)
            logger (AMDSMILogger) - Logger for accessing config values
        return:
            Nothing
        """
        # Set the values for watching as the args will cleared
        watch = args.watch
        watch_time = args.watch_time
        iterations = args.iterations

        # Set the args values to None so we don't loop recursively
        args.watch = None
        args.watch_time = None
        args.iterations = None

        # Set the signal handler to flush a delmiter to file if the format is json
        print("'CTRL' + 'C' to stop watching output:")
        if watch_time:  # Run for set amount of time
            iterations_ran = 0
            end_time = time.time() + watch_time
            while time.time() <= end_time:
                subcommand(args, watching_output=True)
                # Handle iterations limit
                iterations_ran += 1
                if iterations is not None:
                    if iterations <= iterations_ran:
                        break
                time.sleep(watch)
        elif iterations is not None:  # Run for a set amount of iterations
            for iteration in range(iterations):
                subcommand(args, watching_output=True)
                if iteration == iterations - 1:  # Break on iteration completion
                    break
                time.sleep(watch)
        else:  # Run indefinitely as watch_time and iterations are not set
            while True:
                subcommand(args, watching_output=True)
                time.sleep(watch)

        return 1


    def get_gpu_id_from_device_handle(self, input_device_handle):
        """Get the gpu index from the device_handle.
        amdsmi_get_processor_handles() returns the list of device_handles in order of gpu_index
        """
        device_handles = amdsmi_interface.amdsmi_get_processor_handles()
        for gpu_index, device_handle in enumerate(device_handles):
            if input_device_handle.value == device_handle.value:
                return gpu_index
        raise amdsmi_exception.AmdSmiParameterException(input_device_handle,
                                                        amdsmi_interface.amdsmi_wrapper.amdsmi_processor_handle,
                                                        "Unable to find gpu ID from device_handle")
    def get_nic_id_from_device_handle(self, input_device_handle):
        """Get the nic index from the device_handle.
        get_nic_handles() returns the list of device_handles in order of nic_index
        """
        device_handles = amdsmi_interface.get_nic_handles()
        for nic_index, device_handle in enumerate(device_handles):
            if input_device_handle.value == device_handle.value:
                return nic_index
        raise amdsmi_exception.AmdSmiParameterException(input_device_handle,
                                                        amdsmi_interface.amdsmi_wrapper.amdsmi_processor_handle,
                                                        "Unable to find nic ID from device_handle")

    def get_switch_id_from_device_handle(self, input_device_handle):
        """Get the nic index from the device_handle.
        get_nic_handles() returns the list of device_handles in order of nic_index
        """
        device_handles = amdsmi_interface.get_switch_handles()
        for switch_index, device_handle in enumerate(device_handles):
            if input_device_handle.value == device_handle.value:
                return switch_index
        raise amdsmi_exception.AmdSmiParameterException(input_device_handle,
                                                        amdsmi_interface.amdsmi_wrapper.amdsmi_processor_handle,
                                                        "Unable to find switch ID from device_handle")

    def get_cpu_id_from_device_handle(self, input_device_handle):
        """Get the cpu index from the device_handle.
        amdsmi_interface.amdsmi_get_cpusocket_handles() returns the list of device_handles in order of cpu_index
        """
        device_handles = amdsmi_interface.amdsmi_get_cpusocket_handles()
        for cpu_index, device_handle in enumerate(device_handles):
            if input_device_handle.value == device_handle.value:
                return cpu_index
        raise amdsmi_exception.AmdSmiParameterException(input_device_handle,
                                                        amdsmi_interface.amdsmi_wrapper.amdsmi_processor_handle,
                                                        "Unable to find cpu ID from device_handle")


    def get_core_id_from_device_handle(self, input_device_handle):
        """Get the core index from the device_handle.
        amdsmi_interface.amdsmi_get_cpusocket_handles() returns the list of device_handles in order of cpu_index
        """
        device_handles = amdsmi_interface.amdsmi_get_cpucore_handles()
        for core_index, device_handle in enumerate(device_handles):
            if input_device_handle.value == device_handle.value:
                return core_index
        raise amdsmi_exception.AmdSmiParameterException(input_device_handle,
                                                        amdsmi_interface.amdsmi_wrapper.amdsmi_processor_handle,
                                                        "Unable to find core ID from device_handle")


    def get_amd_gpu_bdfs(self):
        """Return a list of GPU BDFs visibile to amdsmi

        Returns:
            list[BDF]: List of GPU BDFs
        """
        gpu_bdfs = []
        device_handles = amdsmi_interface.amdsmi_get_processor_handles()

        for device_handle in device_handles:
            bdf = amdsmi_interface.amdsmi_get_gpu_device_bdf(device_handle)
            gpu_bdfs.append(bdf)

        return gpu_bdfs


    def is_amd_device(self, device_handle):
        """ Return whether the specified device is an AMD device or not

        param device: DRM device identifier
        """
        # Get card vendor id
        asic_info = amdsmi_interface.amdsmi_get_gpu_asic_info(device_handle)
        try:
            vendor_value = int(asic_info['vendor_id'], 16)
            return vendor_value == AMD_VENDOR_ID
        except:
            return False

    def get_perf_levels(self):
        perf_levels_str = [clock.name for clock in amdsmi_interface.AmdSmiDevPerfLevel]
        perf_levels_int = list(set(clock.value for clock in amdsmi_interface.AmdSmiDevPerfLevel))
        return perf_levels_str, perf_levels_int

    def get_accelerator_partition_profile_config(self):
        device_handles = amdsmi_interface.amdsmi_get_processor_handles()
        accelerator_partition_profiles = {'profile_indices':[], 'profile_types':[], 'memory_caps': []}
        for dev in device_handles:
            try:
                profile = amdsmi_interface.amdsmi_get_gpu_accelerator_partition_profile_config(dev)
                num_profiles = profile['num_profiles']
                for p in range(num_profiles):
                    accelerator_partition_profiles['profile_indices'].append(str(profile['profiles'][p]['profile_index']))
                    accelerator_partition_profiles['profile_types'].append(profile['profiles'][p]['profile_type'])
                    accelerator_partition_profiles['memory_caps'].append(profile['profiles'][p]['memory_caps'])
                break # Only need to get the profiles for one device
            except amdsmi_interface.AmdSmiLibraryException as e:
                break
        return accelerator_partition_profiles

    def get_accelerator_choices_types_indices(self):
        return_val = ("N/A", {'profile_indices':[], 'profile_types':[]})
        accelerator_partition_profiles = self.get_accelerator_partition_profile_config()
        if len(accelerator_partition_profiles['profile_types']) != 0:
            compute_partitions_str = accelerator_partition_profiles['profile_types'] + accelerator_partition_profiles['profile_indices']
            accelerator_choices = ", ".join(compute_partitions_str)
            return_val = (accelerator_choices, accelerator_partition_profiles)
        return return_val

    def get_memory_partition_types(self):
        memory_partitions_str = [partition.name for partition in amdsmi_interface.AmdSmiMemoryPartitionType]
        if 'UNKNOWN' in memory_partitions_str:
            memory_partitions_str.remove('UNKNOWN')
        return memory_partitions_str


    def get_clock_types(self):
        clock_types_str = [clock.name for clock in amdsmi_interface.AmdSmiClkType]
        clock_types_int = list(set(clock.value for clock in amdsmi_interface.AmdSmiClkType))
        return clock_types_str, clock_types_int


    def get_power_profiles(self):
        power_profiles_str = [profile.name for profile in amdsmi_interface.AmdSmiPowerProfilePresetMasks]
        if 'UNKNOWN' in power_profiles_str:
            power_profiles_str.remove('UNKNOWN')
        return power_profiles_str


    def get_perf_det_levels(self):
        perf_det_level_str = [level.name for level in amdsmi_interface.AmdSmiDevPerfLevel]
        if 'UNKNOWN' in perf_det_level_str:
            perf_det_level_str.remove('UNKNOWN')
        return perf_det_level_str


    def get_power_caps(self):
        device_handles = amdsmi_interface.amdsmi_get_processor_handles()
        power_cap_min = amdsmi_interface.MaxUIntegerTypes.UINT64_T # start out at max and min and then find real min and max
        power_cap_max = 0
        for dev in device_handles:
            power_cap_info = amdsmi_interface.amdsmi_get_power_cap_info(dev)
            if power_cap_info['max_power_cap'] > power_cap_max:
                power_cap_max = power_cap_info['max_power_cap']
            if power_cap_info['min_power_cap'] < power_cap_max:
                power_cap_min = power_cap_info['min_power_cap']
        return (power_cap_min, power_cap_max)


    def get_soc_pstates(self):
        device_handles = amdsmi_interface.amdsmi_get_processor_handles()
        soc_pstate_profile_list = []
        for dev in device_handles:
            try:
                soc_pstate_info = amdsmi_interface.amdsmi_get_soc_pstate(dev)
            except amdsmi_interface.AmdSmiLibraryException as e:
                continue
            for policy in soc_pstate_info['policies']:
                policy_string = f"{policy['policy_id']}: {policy['policy_description']}"
                if not policy_string in soc_pstate_profile_list:
                    soc_pstate_profile_list.append(policy_string)
        if len(soc_pstate_profile_list) == 0:
            soc_pstate_profile_list.append("N/A")
        return soc_pstate_profile_list


    def get_xgmi_plpd_policies(self):
        device_handles = amdsmi_interface.amdsmi_get_processor_handles()
        xgmi_plpd_profile_list = []
        for dev in device_handles:
            try:
                xgmi_plpd_info = amdsmi_interface.amdsmi_get_xgmi_plpd(dev)
            except amdsmi_interface.AmdSmiLibraryException as e:
                continue
            for policy in xgmi_plpd_info['plpds']:
                policy_string = f"{policy['policy_id']}: {policy['policy_description']}"
                if not policy_string in xgmi_plpd_profile_list:
                    xgmi_plpd_profile_list.append(policy_string)
        if len(xgmi_plpd_profile_list) == 0:
            xgmi_plpd_profile_list.append("N/A")
        return xgmi_plpd_profile_list


    def validate_clock_type(self, input_clock_type):
        valid_clock_types_str, valid_clock_types_int = self.get_clock_types()

        valid_clock_input = False
        if isinstance(input_clock_type, str):
            for clock_type in valid_clock_types_str:
                if input_clock_type.lower() == clock_type.lower():
                    input_clock_type = clock_type # Set input_clock_type to enum value in AmdSmiClkType
                    valid_clock_input = True
                    break
        elif isinstance(input_clock_type, int):
            if input_clock_type in valid_clock_types_int:
                input_clock_type = amdsmi_interface.AmdSmiClkType(input_clock_type)
                valid_clock_input = True

        return valid_clock_input, input_clock_type


    def confirm_out_of_spec_warning(self, auto_respond=False):
        """ Print the warning for running outside of specification and prompt user to accept the terms.

        @param auto_respond: Response to automatically provide for all prompts
        """
        print('''
            ******WARNING******\n
            Operating your AMD GPU outside of official AMD specifications or outside of
            factory settings, including but not limited to the conducting of overclocking,
            over-volting or under-volting (including use of this interface software,
            even if such software has been directly or indirectly provided by AMD or otherwise
            affiliated in any way with AMD), may cause damage to your AMD GPU, system components
            and/or result in system failure, as well as cause other problems.
            DAMAGES CAUSED BY USE OF YOUR AMD GPU OUTSIDE OF OFFICIAL AMD SPECIFICATIONS OR
            OUTSIDE OF FACTORY SETTINGS ARE NOT COVERED UNDER ANY AMD PRODUCT WARRANTY AND
            MAY NOT BE COVERED BY YOUR BOARD OR SYSTEM MANUFACTURER'S WARRANTY.
            Please use this utility with caution.
            ''')
        if not auto_respond:
            user_input = input('Do you accept these terms? [y/n] ')
        else:
            user_input = auto_respond
        if user_input in ['y', 'Y', 'yes', 'Yes', 'YES']:
            return
        else:
            sys.exit('Confirmation not given. Exiting without setting value')

    def confirm_changing_memory_partition_gpu_reload_warning(self, auto_respond=False):
        """ Print the warning for running outside of specification and prompt user to accept the terms.

        :param autoRespond: Response to automatically provide for all prompts
        """
        print('''
          ****** WARNING ******\n
          Setting Dynamic Memory (NPS) partition modes require users to quit all GPU workloads.
          AMD SMI will then attempt to change memory (NPS) partition mode.
          Upon a successful set, AMD SMI will then initiate an action to restart AMD GPU driver.
          This action will change all GPU's in the hive to the requested memory (NPS) partition mode.

          Please use this utility with caution.
          ''')
        if not auto_respond:
            user_input = input('Do you accept these terms? [Y/N] ')
        else:
            user_input = auto_respond
        if user_input in ['Yes', 'yes', 'y', 'Y', 'YES']:
            print('')
            return
        else:
            print('Confirmation not given. Exiting without setting value')
            sys.exit(1)

    def is_valid_profile(self, profile):
        profile_presets = amdsmi_interface.amdsmi_wrapper.amdsmi_power_profile_preset_masks_t__enumvalues
        if profile in profile_presets:
            return True, profile_presets[profile]
        else:
            return False, profile_presets.values()


    def convert_bytes_to_readable(self, bytes_input, format_length=None):
        if isinstance(bytes_input, str):
            return "N/A"
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(bytes_input) < 1024:
                if format_length is not None:
                    if bytes_input < 10:
                        return f"{bytes_input:4.3f} {unit}"
                    elif bytes_input < 100:
                        return f"{bytes_input:4.2f} {unit}"
                    elif bytes_input < 1000:
                        return f"{bytes_input:4.1f} {unit}"
                    else:
                        return f"{bytes_input:4.0f} {unit}"
                else:
                    return f"{bytes_input:3.1f} {unit}"
            bytes_input /= 1024
        return f"{bytes_input:.1f} YB"


    def unit_format(self, logger, value, unit):
        """This function will format output with unit based on the logger output format

        params:
            args - argparser args to pass to subcommand
            logger (AMDSMILogger) - Logger to print out output
            value - the value to be formatted
            unit - the unit to be formatted with the value
        return:
            str or dict : formatted output
        """
        if logger.is_json_format():
            return {"value": value, "unit": unit}
        if logger.is_human_readable_format():
            return f"{value} {unit}".rstrip()
        return f"{value}"

    class SI_Unit(float, Enum):
        GIGA = 1000000000  # 10^9
        MEGA = 1000000     # 10^6
        KILO = 1000        # 10^3
        HECTO = 100        # 10^2
        DEKA = 10          # 10^1
        BASE = 1           # 10^0
        DECI = 0.1         # 10^-1
        CENTI = 0.01       # 10^-2
        MILLI = 0.001      # 10^-3
        MICRO = 0.000001   # 10^-6
        NANO = 0.000000001 # 10^-9

    def convert_SI_unit(self, val: Union[int, float], unit_in: SI_Unit, unit_out = SI_Unit.BASE) -> Union[int, float]:
        """This function will convert a value into another
         scientific (SI) unit. Defaults unit_out to SI_Unit.BASE

        params:
            val: int or float unit to convert
            unit_in: Requires using SI_Unit to set current value's SI unit (eg. SI_Unit.MICRO)
            unit_out - Requires using SI_Unit to set current value's SI unit
             default value is SI_Unit.BASE (eg. SI_Unit.MICRO)
        return:
            int or float : converted SI unit of value requested
        """
        if isinstance(val, float):
            return val * unit_in / unit_out
        elif isinstance(val, int):
            return int(float(val) * unit_in / unit_out)
        else:
            raise TypeError("val must be an int or float")

    def get_pci_device_ids(self) -> Set[str]:
        pci_devices_path = "/sys/bus/pci/devices"
        pci_devices: set[str] = set()
        for device in os.listdir(pci_devices_path):
            device_path = os.path.join(pci_devices_path, device, "device")
            try:
                with open(device_path, 'r') as f:
                    device = f.read().strip()
                    pci_devices.add(device)
            except Exception as _:
                continue
        return pci_devices

    def progressbar(self, it, prefix="", size=60, out=sys.stdout):
        count = len(it)
        def show(j):
            x = int(size*j/count)
            print("{}[{}{}] {}/{} secs remain".format(prefix, u"█"*x, "."*(size-x), j, count),
                    end='\r', file=out, flush=True)
        show(0)
        for i, item in enumerate(it):
            yield item
            show(i+1)
        print("\n\n", end='\r', flush=True, file=out)

    def showProgressbar(self, title="", timeInSeconds=13):
        if title != "":
            title += ": "
        for i in self.progressbar(range(timeInSeconds), title, 40):
            time.sleep(1)
