#!/usr/bin/env python3
#
# Copyright (c) 2024 Advanced Micro Devices, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import sys
sys.path.append("/opt/rocm/libexec/amdsmi_cli/")

try:
    import amdsmi
except ImportError:
    raise ImportError("Could not import /opt/rocm/libexec/amdsmi_cli/amdsmi_cli.py")

import unittest
import threading
import multiprocessing
import time
from datetime import datetime

# Note: amdsmi_status_code_to_string is not tested due to the nature and functionality of the AMDSMI Python wrapper.
# The function is to be tested in the future after the wrapper is updated to return status codes after API calls.

def handle_exceptions(func):
    """Exposes, silences, and logs AMD SMI exceptions to users what exception was raised.

        params:
            func: test function(s) that use decorator to expose AMD SMI exceptions
        return:
            On success - original function is returned
            On failure - silences error and prints to user what exception was caught
        """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except amdsmi.AmdSmiRetryException as e:
            print("**** [ERROR] | Test: " + str(func.__name__) + " | Caught AmdSmiRetryException: {}".format(e))
            amdsmi.amdsmi_shut_down()
            pass
        except amdsmi.AmdSmiTimeoutException as e:
            print("**** [ERROR] | Test: " + str(func.__name__) + " | Caught AmdSmiTimeoutException: {}".format(e))
            amdsmi.amdsmi_shut_down()
            pass
        except amdsmi.AmdSmiLibraryException as e:
            print("**** [ERROR] | Test: " + str(func.__name__) + " | Caught AmdSmiLibraryException: {}".format(e))
            amdsmi.amdsmi_shut_down()
            pass
        except Exception as e:
            print("**** [ERROR] | Test: " + str(func.__name__) + " | Caught unknown exception: {}".format(e))
            amdsmi.amdsmi_shut_down()
            pass
    return wrapper

class TestAmdSmiInit(unittest.TestCase):
    @handle_exceptions
    def test_init(self):
        amdsmi.amdsmi_init()
        amdsmi.amdsmi_shut_down()

class TestAmdSmiPythonInterface(unittest.TestCase):
    @handle_exceptions
    def setUp(self):
        amdsmi.amdsmi_init()

    @handle_exceptions
    def tearDown(self):
        amdsmi.amdsmi_shut_down()

    #Results of test can return 1 of 3 values per functional group:
    #    Pass: Test ran to completion with no errors
    #    Fail: Test ran to completion with 1 or more errors
    #    PassNA: Test cannot be run on this platform
    #        Hardware is not present.  Ex. Trying to test fan speed when no fans are present
    #        ASIC not supported for this test
    #    FailEx: Test did not finish
    #        An uncaught exception occurred
    #        Test was interrupted.  Ex. power failure or User input

    Pass = 0
    Not_Supported = 1
    Fail = 2
    Exception = 3

    def Print(self, string='', myend='\n'):
        tab_len = 4
        if myend == '\n':
            print(string.expandtabs(tab_len))
        else:
            print(string.expandtabs(tab_len), end=myend)
        return

    # Return a value between min and max that is not current or default
    def GetUniqueValue(self, current_value, min_value, max_value, default_value):
        avg_value = int((min_value + max_value) / 2.0)
        value = avg_value
        if value != current_value and value != default_value:
            return value
        value = int(avg_value * 1.10)
        if value >= max_value:
            value = max_value -1
        if value == current_value or value == default_value:
            value = int(avg_value * 0.90)
            if value <= min_value:
                value = min_value +1
        if value == current_value or value == default_value:
            value = avg_value
        return value

    def GetUniqueIndex(self, current_index, min_index, max_index, default_index):
        avg_index = int(round((min_value + max_value) / 2.0))
        index = avg_index
        while(index < max_index):
            if index != current_index and index != default_index:
                return index
            index += 1
        index = avg_index
        while(index > min_index):
            if index != current_index and index != default_index:
                return index
            index -= 1
        index = avg_index
        return index

    def VerifySetByEnum(self, funcGetValue, funcSetValue, gpu, values, value_default=None):
        if not value_default:
            value_default = funcGetValue(gpu)
        self.Print(f'\t\t{"default"}: {values[value_default][0]}\n')

        num_pass = 0
        num_passNA = 0
        num_fail = 0
        num_failEx = 0
        for value in values:
            try:
                value_before = funcGetValue(gpu)
                rc = funcSetValue(gpu, values[value][1])
                if rc:
                    if values[value][2] == self.Exception:
                        num_pass += 1
                        self.Print(f'\t\t   Set: {values[value][0]} Expected exception thrown')
                        self.Print(f'\t\tPass')
                    elif values[value][2] == self.Not_Supported:
                        num_passNA += 1
                        self.Print(f'\t\t   Set: {values[value][0]} Not Supported')
                        self.Print(f'\t\tPassNA')
                    else:
                        self.Print(f'\t\t   Set: {values[value][0]} Exception thrown')
                        num_failEx += 1
                        self.Print(f'\t\tFailEx')
                    self.Print(f'')
                    continue
                value_after = funcGetValue(gpu)
            except:
                self.Print(f'Unexpected Exception occurred')
                num_failEx += 1

            self.Print(f'\t\tBefore: {values[value_before][0]}')
            self.Print(f'\t\t   Set: {values[value][0]}')
            self.Print(f'\t\t After: {values[value_after][0]}')
            if value == value_after:
                num_pass += 1
                self.Print(f'\t\tPass')
            else:
                num_fail += 1
                self.Print(f'\t\tFail')
            self.Print(f'')

        funcSetValue(gpu, values[value_default][1])
        return (num_pass, num_passNA, num_fail, num_failEx)

    #Get, Set, Get
    #    Get initial value
    #    Pass expected: (Change set values)
    #        Set to valid value, check
    #        Set to max value, check
    #        Set to min value, check
    #    Fail expected: (Change set values)
    #        Set to max+1 value, check
    #        Set to max*100 value, check
    #        Set to min-1 or 0 whichever value is valid, check
    #        Set to min-min*100 or 0 whichever value is valid, check
    #        Do a zero check, min may not accept negative values
    #        Set to initial value, check
    #
    #Get, Reset, Get
    #    Get initial value
    #    Reset, check
    #    Set to initial value, check
    #
    #Get, Set, Get, Reset, Get
    #    Get initial value
    #    Set Max/Min, check
    #    Reset, check
    #    Set initial value, check
    #
    def GetSetGet_ByValue(self, funcInfo, funcGetValue, funcSetValue, gpu, arg1=None):
        def _GetSetGet(gpu, value_new, arg1):
            msg = None
            value_before = funcGetValue(gpu, arg1)
            try:
                funcSetValue(gpu, value_new, arg1)
            except:
                msg = '\t\tException occured'
            value_after = funcGetValue(gpu, arg1)
            self.Print(f'\t\tBefore: {value_before}')
            self.Print(f'\t\t   Set: {value_new}')
            self.Print(f'\t\t After: {value_after}')
            if msg:
                self.Print(msg)
            return (value_before, value_new, value_after)

        num_pass = 0
        num_fail = 0

        value_current, value_min, value_max, value_default = funcInfo(gpu, arg1)
        if value_min == value_max:
            self.Print(f'Error: Min == Max, {value_min}, cannot be the same')
            return (num_pass, num_fail)

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Set to valid value')
        value_new = self.GetUniqueValue(value_current, value_min, value_max, value_default)
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected current({value_new}) == after({value_after})')
        if value_new == value_after:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Set to max value')
        value_new = value_max
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected current({value_new}) == after({value_after})')
        if value_new == value_after:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Set to min value')
        value_new = value_min
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected current({value_new}) == after({value_after})')
        if value_new == value_after:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Set to max+1 value')
        value_new = value_max +1
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected after({value_after}) == before({value_before})')
        if value_after == value_before:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Set to max*100 value')
        value_new = value_max * 100
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected after({value_after}) == before({value_before})')
        if value_after == value_before:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Fail: Set to max(0, min-1)')
        value_new = max(0, value_min -1)
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected after({value_after}) == before({value_before})')
        if value_after == value_before:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get, Fail: Set to max(0, min-min*100)')
        value_new = max(0, value_min - value_min*100)
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected after({value_after}) == before({value_before})')
        if value_after == value_before:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Reset Get, Pass')
        value_new = value_default
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected default({value_new}) == after({value_after})')
        if value_default == value_after:
            num_pass += 1
            self.Print(f'\tPass')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        self.Print('#'*50)
        self.Print(f'\tTest Get Set Get Reset Get, Pass')
        value_new = self.GetUniqueValue(value_current, value_min, value_max, value_default)
        value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
        self.Print(f'\tExpected current({value_new}) == after({value_after})')
        if value_new == value_after:
            value_new = value_default
            value_before, value_new, value_after = _GetSetGet(gpu, value_new, arg1)
            self.Print(f'\tExpected default({value_new}) == after({value_after})')
            if value_default == value_after:
                num_pass += 1
                self.Print(f'\tPass')
            else:
                num_fail += 1
                self.Print(f'\tFail')
        else:
            num_fail += 1
            self.Print(f'\tFail')

        # Return machine to default value
        funcSetValue(gpu, value_default, arg1)

        return (num_pass, num_fail)


    def GetSetGet_ByIndex(self, funcInfo, funcGetValue, funcSetValue, gpu, arg1=None):
        pass


    def GetSetGet_ByBitmask(self, funcInfo, funcGetValue, funcSetValue, gpu, arg1=None):
        pass

#jcnii
    @handle_exceptions
    def test_XXX(self):
        def Get_XXX_Info(gpu, arg1=0):
            try:
                value_current = amdsmi.amdsmi_get_XXX(gpu, arg1)
                value_min = 0
                value_max = 0
                value_default = 0
                # value_rpms = amdsmi.amdsmi_get_gpu_fan_rpms(gpu, arg1)
            except:
                value_current = 0
                value_min = 0
                value_max = 0
                value_default = 0
            return (value_current, value_min, value_max, value_default)
        def Get_XXX_Value(gpu, arg1=0):
            value_current = amdsmi.amdsmi_XXX(gpu, arg1)
            return value_current
        def Set_XXX_Value(gpu, value, arg1=0):
            amdsmi.amdsmi_set_XXX(gpu, arg1, value)
            return

        funcInfo = Get_XXX_Info
        funcGetValue = Get_XXX_Value
        funcSetValue = Set_XXX_Value
        return

    def test_asic_kfd_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_asic_info \n")
            asic_info = amdsmi.amdsmi_get_gpu_asic_info(processors[i])
            print("  asic_info['market_name'] is: {}".format(
                asic_info['market_name']))
            print("  asic_info['vendor_id'] is: {}".format(
                asic_info['vendor_id']))
            print("  asic_info['vendor_name'] is: {}".format(
                asic_info['vendor_name']))
            print("  asic_info['device_id'] is: {}".format(
                asic_info['device_id']))
            print("  asic_info['rev_id'] is: {}".format(
                asic_info['rev_id']))
            print("  asic_info['asic_serial'] is: {}".format(
                asic_info['asic_serial']))
            print("  asic_info['oam_id'] is: {}".format(
                asic_info['oam_id']))
            print("  asic_info['target_graphics_version'] is: {}".format(
                asic_info['target_graphics_version']))
            print("  asic_info['num_compute_units'] is: {}".format(
                asic_info['num_compute_units']))
            print("\n###Test amdsmi_get_gpu_kfd_info \n")
            kfd_info = amdsmi.amdsmi_get_gpu_kfd_info(processors[i])
            print("  kfd_info['kfd_id'] is: {}".format(
                kfd_info['kfd_id']))
            print("  kfd_info['node_id'] is: {}".format(
                kfd_info['node_id']))
            print("  kfd_info['current_partition_id'] is: {}\n".format(
                kfd_info['current_partition_id']))
        print()
        self.tearDown()

    # amdsmi_get_gpu_bad_page_info is not supported in Navi2x, Navi3x
    @handle_exceptions
    def test_bad_page_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            processor = amdsmi.amdsmi_get_processor_handle_from_bdf(bdf)
            print("\n###Test amdsmi_get_gpu_bad_page_info \n")
            bad_page_info = amdsmi.amdsmi_get_gpu_bad_page_info(processors[i])
            print("bad_page_info: " + str(bad_page_info))
            print("Number of bad pages: {}".format(len(bad_page_info)))
            j = 0
            for table_record in bad_page_info:
                print("\ntable_record[\"value\"]" + str(table_record["value"]))
                print("Page: {}".format(j))
                print("Page Address: " + str(table_record["page_address"]))
                print("Page Size: " + str(table_record["page_size"]))
                print("Status: " + str(table_record["status"]))
                print()
                j += 1
        print()
        self.tearDown()

    def test_bdf_device_id(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_processor_handle_from_bdf \n")
            processor = amdsmi.amdsmi_get_processor_handle_from_bdf(bdf)
            print("\n###Test amdsmi_get_gpu_vbios_info \n")
            vbios_info = amdsmi.amdsmi_get_gpu_vbios_info(processor)
            print("  vbios_info['part_number'] is: {}".format(
                vbios_info['part_number']))
            print("  vbios_info['build_date'] is: {}".format(
                vbios_info['build_date']))
            print("  vbios_info['version'] is: {}".format(
                vbios_info['version']))
            print("  vbios_info['name'] is: {}".format(
                vbios_info['name']))
            print("\n###Test amdsmi_get_gpu_device_uuid \n")
            uuid = amdsmi.amdsmi_get_gpu_device_uuid(processor)
            print("  uuid is: {}".format(uuid))
        print()
        self.tearDown()

    def test_board_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_board_info \n")
            board_info = amdsmi.amdsmi_get_gpu_board_info(processors[i])
            print("  board_info['model_number'] is: {}".format(
                board_info['model_number']))
            print("  board_info['product_serial'] is: {}".format(
                board_info['product_serial']))
            print("  board_info['fru_id'] is: {}".format(
                board_info['fru_id']))
            print("  board_info['manufacturer_name'] is: {}".format(
                board_info['manufacturer_name']))
            print("  board_info['product_name'] is: {}".format(
                board_info['product_name']))
        print()
        self.tearDown()

    def test_clock_frequency(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_clk_freq \n")
            clock_frequency = amdsmi.amdsmi_get_clk_freq(
                processors[i], amdsmi.AmdSmiClkType.SYS)
            print("  SYS clock_frequency['num_supported']: {}".format(
                clock_frequency['num_supported']))
            print("  SYS clock_frequency['current']: {}".format(
                clock_frequency['current']))
            print("  SYS clock_frequency['frequency']: {}".format(
                clock_frequency['frequency']))
            clock_frequency = amdsmi.amdsmi_get_clk_freq(
                processors[i], amdsmi.AmdSmiClkType.DF)
            print("  DF clock_frequency['num_supported']: {}".format(
                clock_frequency['num_supported']))
            print("  DF clock_frequency['current']: {}".format(
                clock_frequency['current']))
            print("  DF clock_frequency['frequency']: {}".format(
                clock_frequency['frequency']))
        print()
        self.tearDown()

    # amdsmi_get_clk_freq with AmdSmiClkType.DCEF is not supported in MI210, MI300A
    @handle_exceptions
    def test_clock_frequency_DCEF(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_clk_freq \n")
            clock_frequency = amdsmi.amdsmi_get_clk_freq(
                processors[i], amdsmi.AmdSmiClkType.DCEF)
            print("  DCEF clock_frequency['num_supported']: {}".format(
                clock_frequency['num_supported']))
            print("  DCEF clock_frequency['current']: {}".format(
                clock_frequency['current']))
            print("  DCEF clock_frequency['frequency']: {}".format(
                clock_frequency['frequency']))
        print()
        self.tearDown()

    def test_clock_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_clock_info \n")
            clock_measure = amdsmi.amdsmi_get_clock_info(
                    processors[i], amdsmi.AmdSmiClkType.GFX)
            print("  Current clock for domain GFX is: {}".format(
                clock_measure['clk']))
            print("  Max clock for domain GFX is: {}".format(
                clock_measure['max_clk']))
            print("  Min clock for domain GFX is: {}".format(
                clock_measure['min_clk']))
            print("  Is GFX clock locked: {}".format(
                clock_measure['clk_locked']))
            print("  Is GFX clock in deep sleep: {}".format(
                clock_measure['clk_deep_sleep']))
            clock_measure = amdsmi.amdsmi_get_clock_info(
                processors[i], amdsmi.AmdSmiClkType.MEM)
            print("  Current clock for domain MEM is: {}".format(
                clock_measure['clk']))
            print("  Max clock for domain MEM is: {}".format(
                clock_measure['max_clk']))
            print("  Min clock for domain MEM is: {}".format(
                clock_measure['min_clk']))
            print("  Is MEM clock in deep sleep: {}".format(
                clock_measure['clk_deep_sleep']))
        print()
        self.tearDown()

    # AmdSmiClkType.VCLK0 and DCLK0 are not supported in MI210
    @handle_exceptions
    def test_clock_info_vclk0_dclk0(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_clock_info \n")
            clock_measure = amdsmi.amdsmi_get_clock_info(
                processors[i], amdsmi.AmdSmiClkType.VCLK0)
            print("  Current clock for domain VCLK0 is: {}".format(
                clock_measure['clk']))
            print("  Max clock for domain VCLK0 is: {}".format(
                clock_measure['max_clk']))
            print("  Min clock for domain VCLK0 is: {}".format(
                clock_measure['min_clk']))
            print("  Is VCLK0 clock in deep sleep: {}".format(
                clock_measure['clk_deep_sleep']))
            clock_measure = amdsmi.amdsmi_get_clock_info(
                processors[i], amdsmi.AmdSmiClkType.DCLK0)
            print("  Current clock for domain DCLK0 is: {}".format(
                clock_measure['clk']))
            print("  Max clock for domain DCLK0 is: {}".format(
                clock_measure['max_clk']))
            print("  Min clock for domain DCLK0 is: {}".format(
                clock_measure['min_clk']))
            print("  Is DCLK0 clock in deep sleep: {}".format(
                clock_measure['clk_deep_sleep']))
        print()
        self.tearDown()

    # AmdSmiClkType.VCLK1 and DCLK1 are not supported in MI210, MI300A, MI300X
    @handle_exceptions
    def test_clock_info_vclk1_dclk1(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_clock_info \n")
            clock_measure = amdsmi.amdsmi_get_clock_info(
                processors[i], amdsmi.AmdSmiClkType.VCLK1)
            print("  Current clock for domain VCLK1 is: {}".format(
                clock_measure['clk']))
            print("  Max clock for domain VCLK1 is: {}".format(
                clock_measure['max_clk']))
            print("  Min clock for domain VCLK1 is: {}".format(
                clock_measure['min_clk']))
            print("  Is VCLK1 clock in deep sleep: {}".format(
                clock_measure['clk_deep_sleep']))
            clock_measure = amdsmi.amdsmi_get_clock_info(
                processors[i], amdsmi.AmdSmiClkType.DCLK1)
            print("  Current clock for domain DCLK1 is: {}".format(
                clock_measure['clk']))
            print("  Max clock for domain DCLK1 is: {}".format(
                clock_measure['max_clk']))
            print("  Min clock for domain DCLK1 is: {}".format(
                clock_measure['min_clk']))
            print("  Is DCLK1 clock in deep sleep: {}".format(
                clock_measure['clk_deep_sleep']))
        print()
        self.tearDown()

    #frequencies_read_write
    #    amdsmi_get_clk_freq()
    #    amdsmi_set_clk_freq()
    #    amdsmi_set_gpu_clk_range() # deprecated
    #    amdsmi_set_gpu_clk_limit()
    # TODO: Needs work
    @handle_exceptions
    def test_clock_freq_NEW(self):
        def Get_Clock_Info(gpu, clock_type):
            try:
                # Gets values
                info = amdsmi.amdsmi_get_clock_info(gpu, clock_type)
                value_current = info['clk']
                value_min = info['min_clk']
                value_max = info['max_clk']
                value_default = 0
                #clk_locked = info['clk_locked']
                #clk_deep_sleep = info['clk_deep_sleep']
            except:
                value_current = 0
                value_min = 0
                value_max = 0
                value_default = 0
            return (value_current, value_min, value_max, value_default)
        def Set_Clock_Info(gpu, value_min, value_max, clock_type):
            try:
                # amdsmi.amdsmi_set_gpu_clk_range(gpu, value_min, value_max, clock_type)
                amdsmi.amdsmi_set_gpu_clk_limit(gpu, clock_type, amdsmi.CLK_LIMIT_MIN, value_min)
                amdsmi.amdsmi_set_gpu_clk_limit(gpu, clock_type, amdsmi.CLK_LIMIT_MAX, value_max)
            except:
                self.Print('\t\tException thrown')
            return (value_current, value_min, value_max, value_default)
        def Get_Clock_Value(gpu, clock_type):
            try:
                info = amdsmi.amdsmi_get_clk_freq(gpu, clock_type)
            except:
                return -1, 0, [], 0

            num_supported = info['num_supported']
            current = info['current']
            frequency = info['frequency']
            if not num_supported or current < 0 or current >= num_supported:
                return -1, 0, [], 0
            value_current = round(frequency[current] / 100000.0)
            return num_supported, current, frequency, value_current
        def Set_Clock_Value(gpu, value_bitmask, clock_type):
            try:
                amdsmi.amdsmi_set_clk_freq(gpu, clock_type, value_bitmask)
            except:
                self.Print('\t\tException thrown')
                pass
            return

        funcInfo = Get_Clock_Info
        funcGetValue = Get_Clock_Value
        funcSetValue = Set_Clock_Value

        clock_types = \
        [
            ['SYS',   amdsmi.AmdSmiClkType.SYS],
            ['GFX',   amdsmi.AmdSmiClkType.GFX],
            ['DF',    amdsmi.AmdSmiClkType.DF],
            ['DCEF',  amdsmi.AmdSmiClkType.DCEF],
            ['SOC',   amdsmi.AmdSmiClkType.SOC],
            ['MEM',   amdsmi.AmdSmiClkType.MEM],
            ['PCIE',  amdsmi.AmdSmiClkType.PCIE],
            ['VCLK0', amdsmi.AmdSmiClkType.VCLK0],
            ['VCLK1', amdsmi.AmdSmiClkType.VCLK1],
            ['DCLK0', amdsmi.AmdSmiClkType.DCLK0],
            ['DCLK1', amdsmi.AmdSmiClkType.DCLK1]
        ]

        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        self.Print()
        self.Print('#'*80)
        self.Print('Test clock_freq')
        for clock_name, clock_type in clock_types:
            num_pass = 0
            num_passNA = 0
            num_fail = 0
            num_failEx = 0
            for i in range(0, len(processors)):
                amdsmi.amdsmi_set_gpu_perf_level(processors[i], amdsmi.AmdSmiDevPerfLevel.MANUAL)
                time.sleep(1)
                self.Print('#'*50)
                self.Print(f'\tClock Info(gpu={i}, clock_type={clock_name})')
                value_current, value_min, value_max, value_default = funcInfo(processors[i], clock_type)
                str_len = len('default')
                self.Print(f'\t\t{"current":{str_len}s}: {value_current}')
                self.Print(f'\t\t{"min":{str_len}s}: {value_min}')
                self.Print(f'\t\t{"max":{str_len}s}: {value_max}')
                self.Print(f'\t\t{"default":{str_len}s}: {value_default}')

                _num_pass = []
                _num_passNA = []
                _num_fail = []
                _num_failEx = []

                num_supported, current, frequency, value_current = Get_Clock_Value(processors[i], clock_type)
                self.Print(f'\t\tTest clock {clock_name}, {num_supported} frequencies')
                if num_supported < 0:
                    self.Print('\t\t\tNot Supported')
                    _num_passNA.append(0)
                for j in range(num_supported):
                    try:
                        Set_Clock_Value(processors[i], 1<<j, clock_type)
                        time.sleep(1)
                        _, current, _, _ = Get_Clock_Value(processors[i], clock_type)
                        if current < 0:
                            break
                        if current == j:
                            _num_pass.append(j)
                        else:
                            _num_fail.append(j)
                    except:
                        _num_failEx.append(j)

                if len(_num_fail) or len(_num_failEx):
                    if len(_num_fail):
                        num_fail += 1
                    if len(_num_failEx):
                        num_failEx += 1
                else:
                    if len(_num_pass):
                        num_pass += 1
                    if len(_num_passNA):
                        num_passNA += 1
                self.Print(f'\t\tPass   : {len(_num_pass):2d}, freq_indicies={_num_pass}')
                self.Print(f'\t\tPassNA : {len(_num_passNA):2d}, freq_indicies={_num_passNA}')
                self.Print(f'\t\tFail   : {len(_num_fail):2d}, freq_indicies={_num_fail}')
                self.Print(f'\t\tFailEx : {len(_num_failEx):2d}, freq_indicies={_num_failEx}')

                # Reset
                if num_supported >= 0:
                    Set_Clock_Value(processors[i], 1<<0, clock_type)

            self.Print()
            self.Print(f'\tPass   : {num_pass:2d}')
            self.Print(f'\tPassNA : {num_passNA:2d}')
            self.Print(f'\tFail   : {num_fail:2d}')
            self.Print(f'\tFailEx : {num_failEx:2d}')
        self.Print()
        self.tearDown()
        return

    #perf_level_read_write
    #    amdsmi_get_gpu_perf_level()
    #    amdsmi_set_gpu_perf_level()
    @handle_exceptions
    def test_gpu_perf_level_NEW(self):
        def Get_Perf_Level_Value(gpu):
            value_current = amdsmi.amdsmi_get_gpu_perf_level(gpu)
            return value_current
        def Set_Perf_Level_Value(gpu, perf_level):
            #Return:
            #  pass = 0
            #  fail = 1
            #  fail = 2 exception
            try:
                amdsmi.amdsmi_set_gpu_perf_level(gpu, perf_level)
            except:
                return 2
            return 0

        funcGetValue = Get_Perf_Level_Value
        funcSetValue = Set_Perf_Level_Value

        perf_levels = \
        {
            "AMDSMI_DEV_PERF_LEVEL_AUTO": ['AUTO', amdsmi.AmdSmiDevPerfLevel.AUTO, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_LOW": ['LOW', amdsmi.AmdSmiDevPerfLevel.LOW, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_HIGH": ['HIGH', amdsmi.AmdSmiDevPerfLevel.HIGH, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_MANUAL": ['MANUAL', amdsmi.AmdSmiDevPerfLevel.MANUAL, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_STABLE_STD": ['STABLE_STD', amdsmi.AmdSmiDevPerfLevel.STABLE_STD, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_STABLE_PEAK": ['STABLE_PEAK', amdsmi.AmdSmiDevPerfLevel.STABLE_PEAK, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_STABLE_MIN_MCLK": ['STABLE_MIN_MCLK', amdsmi.AmdSmiDevPerfLevel.STABLE_MIN_MCLK, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_STABLE_MIN_SCLK": ['STABLE_MIN_SCLK', amdsmi.AmdSmiDevPerfLevel.STABLE_MIN_SCLK, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_DETERMINISM": ['DETERMINISM', amdsmi.AmdSmiDevPerfLevel.DETERMINISM, self.Pass],
            "AMDSMI_DEV_PERF_LEVEL_UNKNOWN": ['UNKNOWN', amdsmi.AmdSmiDevPerfLevel.UNKNOWN, self.Exception]
        }

        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        self.Print()
        self.Print('#'*80)
        self.Print('Test GPU Perf Levels')
        for i in range(0, len(processors)):
            self.Print('#'*50)
            self.Print(f'\tPerf Level({i})')
            num_pass, num_passNA, num_fail, num_failEx = self.VerifySetByEnum(funcGetValue, funcSetValue, processors[i], perf_levels, 'AMDSMI_DEV_PERF_LEVEL_MANUAL')
            self.Print()
            self.Print(f'\tPass   : {num_pass:2d}')
            self.Print(f'\tPassNA : {num_passNA:2d}')
            self.Print(f'\tFail   : {num_fail:2d}')
            self.Print(f'\tFailEx : {num_failEx:2d}')
        self.Print()
        self.tearDown()
        return

    def test_driver_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_driver_info \n")
            driver_info = amdsmi.amdsmi_get_gpu_driver_info(processors[i])
            print("Driver info:  {}".format(driver_info))
        print()
        self.tearDown()

    # amdsmi_get_gpu_ecc_count is not supported in Navi2x, Navi3x, MI210, MI300A
    @handle_exceptions
    def test_ecc_count_block(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        gpu_blocks = {
            "INVALID": amdsmi.AmdSmiGpuBlock.INVALID,
            "UMC": amdsmi.AmdSmiGpuBlock.UMC,
            "SDMA": amdsmi.AmdSmiGpuBlock.SDMA,
            "GFX": amdsmi.AmdSmiGpuBlock.GFX,
            "MMHUB": amdsmi.AmdSmiGpuBlock.MMHUB,
            "ATHUB": amdsmi.AmdSmiGpuBlock.ATHUB,
            "PCIE_BIF": amdsmi.AmdSmiGpuBlock.PCIE_BIF,
            "HDP": amdsmi.AmdSmiGpuBlock.HDP,
            "XGMI_WAFL": amdsmi.AmdSmiGpuBlock.XGMI_WAFL,
            "DF": amdsmi.AmdSmiGpuBlock.DF,
            "SMN": amdsmi.AmdSmiGpuBlock.SMN,
            "SEM": amdsmi.AmdSmiGpuBlock.SEM,
            "MP0": amdsmi.AmdSmiGpuBlock.MP0,
            "MP1": amdsmi.AmdSmiGpuBlock.MP1,
            "FUSE": amdsmi.AmdSmiGpuBlock.FUSE,
            "MCA": amdsmi.AmdSmiGpuBlock.MCA,
            "VCN": amdsmi.AmdSmiGpuBlock.VCN,
            "JPEG": amdsmi.AmdSmiGpuBlock.JPEG,
            "IH": amdsmi.AmdSmiGpuBlock.IH,
            "MPIO": amdsmi.AmdSmiGpuBlock.MPIO,
            "RESERVED": amdsmi.AmdSmiGpuBlock.RESERVED
        }
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_ecc_count \n")
            for block_name, block_code in gpu_blocks.items():
                ecc_count = amdsmi.amdsmi_get_gpu_ecc_count(
                    processors[i], block_code)
                print("  Number of uncorrectable errors for {}: {}".format(
                    block_name, ecc_count['uncorrectable_count']))
                print("  Number of correctable errors for {}: {}".format(
                    block_name, ecc_count['correctable_count']))
                print("  Number of deferred errors for {}: {}".format(
                    block_name, ecc_count['deferred_count']))
                self.assertGreaterEqual(ecc_count['uncorrectable_count'], 0)
                self.assertGreaterEqual(ecc_count['correctable_count'], 0)
                self.assertGreaterEqual(ecc_count['deferred_count'], 0)
            print()
        print()
        self.tearDown()

    def test_ecc_count_total(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_total_ecc_count \n")
            ecc_info = amdsmi.amdsmi_get_gpu_total_ecc_count(processors[i])
            print("Number of uncorrectable errors: {}".format(
                ecc_info['uncorrectable_count']))
            print("Number of correctable errors: {}".format(
                ecc_info['correctable_count']))
            print("Number of deferred errors: {}".format(
                ecc_info['deferred_count']))
            self.assertGreaterEqual(ecc_info['uncorrectable_count'], 0)
            self.assertGreaterEqual(ecc_info['correctable_count'], 0)
            self.assertGreaterEqual(ecc_info['deferred_count'], 0)
        print()
        self.tearDown()

    def test_fw_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_fw_info \n")
            fw_info = amdsmi.amdsmi_get_fw_info(processors[i])
            fw_num = len(fw_info['fw_list'])
            self.assertLessEqual(fw_num, len(amdsmi.AmdSmiFwBlock))
            for j in range(0, fw_num):
                fw = fw_info['fw_list'][j]
                if fw['fw_version'] != 0:
                    print("  FW name:           {}".format(
                        fw['fw_name'].name))
                    print("  FW version:        {}".format(
                        fw['fw_version']))
        print()
        self.tearDown()

    def test_gpu_activity(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_activity \n")
            engine_usage = amdsmi.amdsmi_get_gpu_activity(processors[i])
            print("  engine_usage['gfx_activity'] is: {} %".format(
                engine_usage['gfx_activity']))
            print("  engine_usage['umc_activity'] is: {} %".format(
                engine_usage['umc_activity']))
            print("  engine_usage['mm_activity'] is: {} %".format(
                engine_usage['mm_activity']))
        print()
        self.tearDown()

    def test_memory_usage(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_memory_usage \n")
            memory_usage = amdsmi.amdsmi_get_gpu_memory_usage(
                processors[i], amdsmi.AmdSmiMemoryType.VRAM)
            print("  memory_usage for VRAM is: {}".format(memory_usage))
            memory_usage = amdsmi.amdsmi_get_gpu_memory_usage(
                processors[i], amdsmi.AmdSmiMemoryType.VIS_VRAM)
            print("  memory_usage for VIS_VRAM is: {}".format(memory_usage))
            memory_usage = amdsmi.amdsmi_get_gpu_memory_usage(
                processors[i], amdsmi.AmdSmiMemoryType.GTT)
            print("  memory_usage for GTT is: {}".format(memory_usage))
        print()
        self.tearDown()

    def test_pcie_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_pcie_info \n")
            pcie_info = amdsmi.amdsmi_get_pcie_info(processors[i])
            print("  pcie_info['pcie_metric']['pcie_width'] is: {}".format(
                pcie_info['pcie_metric']['pcie_width']))
            print("  pcie_info['pcie_static']['max_pcie_width'] is: {} ".format(
                pcie_info['pcie_static']['max_pcie_width']))
            print("  pcie_info['pcie_metric']['pcie_speed'] is: {} MT/s".format(
                pcie_info['pcie_metric']['pcie_speed']))
            print("  pcie_info['pcie_static']['max_pcie_speed'] is: {} ".format(
                pcie_info['pcie_static']['max_pcie_speed']))
            print("  pcie_info['pcie_static']['pcie_interface_version'] is: {}".format(
                pcie_info['pcie_static']['pcie_interface_version']))
            print("  pcie_info['pcie_static']['slot_type'] is: {}".format(
                pcie_info['pcie_static']['slot_type']))
            print("  pcie_info['pcie_metric']['pcie_replay_count'] is: {}".format(
                pcie_info['pcie_metric']['pcie_replay_count']))
            print("  pcie_info['pcie_metric']['pcie_bandwidth'] is: {}".format(
                pcie_info['pcie_metric']['pcie_bandwidth']))
            print("  pcie_info['pcie_metric']['pcie_l0_to_recovery_count'] is: {}".format(
                pcie_info['pcie_metric']['pcie_l0_to_recovery_count']))
            print("  pcie_info['pcie_metric']['pcie_replay_roll_over_count'] is: {}".format(
                pcie_info['pcie_metric']['pcie_replay_roll_over_count']))
            print("  pcie_info['pcie_metric']['pcie_nak_sent_count'] is: {}".format(
                pcie_info['pcie_metric']['pcie_nak_sent_count']))
            print("  pcie_info['pcie_metric']['pcie_nak_received_count'] is: {}".format(
                pcie_info['pcie_metric']['pcie_nak_received_count']))
            print("  pcie_info['pcie_metric']['pcie_lc_perf_other_end_recovery_count'] is: {}".format(
                pcie_info['pcie_metric']['pcie_lc_perf_other_end_recovery_count']))
        print()
        self.tearDown()

    def test_power_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            self.Print(f'\n\n###Test Processor {i}, bdf: {bdf}')
            self.Print('\n###Test amdsmi_get_power_info\n')
            power_info = amdsmi.amdsmi_get_power_info(processors[i])
            self.Print(f'\tcurrent_socket_power is: {power_info["current_socket_power"]}')
            self.Print(f'\taverage_socket_power is: {power_info["average_socket_power"]}')
            self.Print(f'\tgfx_voltage is: {power_info["gfx_voltage"]}')
            self.Print(f'\tsoc_voltage is: {power_info["soc_voltage"]}')
            self.Print(f'\tmem_voltage is: {power_info["mem_voltage"]}')
            self.Print(f'\tpower_limit is: {power_info["power_limit"]}')
            self.Print('\n###Test amdsmi_get_power_cap_info\n')
            power_cap_info = amdsmi.amdsmi_get_power_cap_info(processors[i])
            self.Print(f'\tdpm_cap is: {power_cap_info["dpm_cap"]}')
            self.Print(f'\tpower_cap is: {power_cap_info["power_cap"]}')
            self.Print('\n###Test amdsmi_is_gpu_power_management_enabled \n')
            is_power_management_enabled = amdsmi.amdsmi_is_gpu_power_management_enabled(processors[i])
            self.Print('\tPower management enabled: {is_power_management_enabled}')
        self.Print()
        self.tearDown()
        return

    #power_cap_read_write
    #    amdsmi_get_power_cap_info()
    #    amdsmi_set_power_cap()
    #    amdsmi_set_power_cap()
    @handle_exceptions
    def test_power_cap_NEW(self):
        def Get_Power_Info(gpu, arg1=None):
            try:
                info = amdsmi.amdsmi_get_power_cap_info(gpu)
                value_current = info['power_cap']
                value_min = info['min_power_cap']
                value_max = info['max_power_cap']
                value_default = info['default_power_cap']
            except:
                value_current = 0
                value_min = 0
                value_max = 0
                value_default = 0
            return (value_current, value_min, value_max, value_default)
        def Get_Power_Value(gpu, arg1=None):
            value_current, _, _, _ = Get_Power_Info(gpu, arg1)
            return value_current
        def Set_Power_Value(gpu, value, arg1=0):
            amdsmi.amdsmi_set_power_cap(gpu, arg1, value)
            return

        funcInfo = Get_Power_Info
        funcGetValue = Get_Power_Value
        funcSetValue = Set_Power_Value

        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        self.Print()
        self.Print('#'*80)
        self.Print('Test power_cap')
        for i in range(0, len(processors)):
            self.Print('#'*50)
            self.Print(f'\tPower Cap Info({i})')
            value_current, value_min, value_max, value_default = funcInfo(processors[i])
            str_len = len('default')
            self.Print(f'\t\t{"current":{str_len}s}: {value_current}')
            self.Print(f'\t\t{"min":{str_len}s}: {value_min}')
            self.Print(f'\t\t{"max":{str_len}s}: {value_max}')
            self.Print(f'\t\t{"default":{str_len}s}: {value_default}')
            num_pass, num_fail = self.GetSetGet_ByValue(funcInfo, funcGetValue, funcSetValue, processors[i], 0)

            self.Print()
            self.Print(f'\tPass : {num_pass:2d}')
            self.Print(f'\tFail : {num_fail:2d}')
        self.Print()
        self.tearDown()
        return

    #fan_read_write
    #    amdsmi_get_gpu_fan_speed()
    #    amdsmi_get_gpu_fan_speed_max()
    #    amdsmi_get_gpu_fan_rpms()
    #    amdsmi_set_gpu_fan_speed()
    #    amdsmi_reset_gpu_fan()
    # TODO: Needs work
    @handle_exceptions
    def test_fan_speed_NEW(self):
        def Get_Fan_Info(gpu, arg1=0):
            try:
                value_current = amdsmi.amdsmi_get_gpu_fan_speed(gpu, arg1)
                value_min = 0
                value_max = amdsmi.amdsmi_get_gpu_fan_speed_max(gpu, arg1)
                value_default = 0
                # value_rpms = amdsmi.amdsmi_get_gpu_fan_rpms(gpu, arg1)
            except:
                value_current = 0
                value_min = 0
                value_max = 0
                value_default = 0
            return (value_current, value_min, value_max, value_default)
        def Get_Fan_Value(gpu, arg1=0):
            value_current = amdsmi.amdsmi_get_gpu_fan_speed(gpu, arg1)
            return value_current
        def Set_Fan_Value(gpu, value, arg1=0):
            amdsmi.amdsmi_set_gpu_fan_speed(gpu, arg1, value)
            return

        funcInfo = Get_Fan_Info
        funcGetValue = Get_Fan_Value
        funcSetValue = Set_Fan_Value

        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        self.Print()
        self.Print('#'*80)
        self.Print('Test fan_speed')
        for i in range(0, len(processors)):
            self.Print('#'*50)
            self.Print(f'\tFan Info({i})')
            value_current, value_min, value_max, value_default = funcInfo(processors[i], 0)
            str_len = len('default')
            self.Print(f'\t\t{"current":{str_len}s}: {value_current}')
            self.Print(f'\t\t{"min":{str_len}s}: {value_min}')
            self.Print(f'\t\t{"max":{str_len}s}: {value_max}')
            self.Print(f'\t\t{"default":{str_len}s}: {value_default}')
            num_pass, num_fail = self.GetSetGet_ByValue(funcInfo, funcGetValue, funcSetValue, processors[i], 0)

            self.Print()
            self.Print(f'\tPass : {num_pass:2d}')
            self.Print(f'\tFail : {num_fail:2d}')
        self.Print()
        self.tearDown()

    def test_process_list(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_process_list \n")
            process_list = amdsmi.amdsmi_get_gpu_process_list(processors[i])
            print("  Process list: {}".format(process_list))
        print()
        self.tearDown()

    def test_processor_type(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_processor_type \n")
            processor_type = amdsmi.amdsmi_get_processor_type(processors[i])
            print("  Processor type is: {}".format(processor_type['processor_type']))
        print()
        self.tearDown()

    # amdsmi_get_gpu_ras_block_features_enabled is not supported in Navi2x, Navi3x
    @handle_exceptions
    def test_ras_block_features_enabled(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_ras_block_features_enabled \n")
            ras_enabled = amdsmi.amdsmi_get_gpu_ras_block_features_enabled(processors[i])
            for j in range(0, len(ras_enabled)):
                print("  RAS status for {} is: {}".format(ras_enabled[j]['block'], ras_enabled[j]['status']))
        print()
        self.tearDown()

    # amdsmi_get_gpu_ras_feature_info is not supported in Navi2x, Navi3x
    @handle_exceptions
    def test_ras_feature_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_ras_feature_info \n")
            ras_feature = amdsmi.amdsmi_get_gpu_ras_feature_info(processors[i])
            if ras_feature != None:
                print("RAS eeprom version: {}".format(ras_feature['eeprom_version']))
                print("RAS parity schema: {}".format(ras_feature['parity_schema']))
                print("RAS single bit schema: {}".format(ras_feature['single_bit_schema']))
                print("RAS double bit schema: {}".format(ras_feature['double_bit_schema']))
                print("Poisoning supported: {}".format(ras_feature['poison_schema']))
        print()
        self.tearDown()

    def test_socket_info(self):
        self.setUp()
        print("\n\n###Test amdsmi_get_socket_handles")
        sockets = amdsmi.amdsmi_get_socket_handles()
        for i in range(0, len(sockets)):
            print("\n\n###Test Socket {}".format(i))
            print("\n###Test amdsmi_get_socket_info \n")
            socket_name = amdsmi.amdsmi_get_socket_info(sockets[i])
            print("  Socket: {}".format(socket_name))
        print()
        self.tearDown()

    def test_temperature_metric(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_temp_metric \n")
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.HOTSPOT, amdsmi.AmdSmiTemperatureMetric.CURRENT)
            print("  Current temperature for HOTSPOT is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.VRAM, amdsmi.AmdSmiTemperatureMetric.CURRENT)
            print("  Current temperature for VRAM is: {}".format(
                temperature_measure))
            print("\n###Test amdsmi_get_temp_metric \n")
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.HOTSPOT, amdsmi.AmdSmiTemperatureMetric.CRITICAL)
            print("  Limit (critical) temperature for HOTSPOT is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.VRAM, amdsmi.AmdSmiTemperatureMetric.CRITICAL)
            print("  Limit (critical) temperature for VRAM is: {}".format(
                temperature_measure))
            print("\n###Test amdsmi_get_temp_metric \n")
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.HOTSPOT, amdsmi.AmdSmiTemperatureMetric.EMERGENCY)
            print("  Shutdown (emergency) temperature for HOTSPOT is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.VRAM, amdsmi.AmdSmiTemperatureMetric.EMERGENCY)
            print("  Shutdown (emergency) temperature for VRAM is: {}".format(
                temperature_measure))
        print()
        self.tearDown()

    # AmdSmiTemperatureType.EDGE is not supported in MI300A, MI300X
    @handle_exceptions
    def test_temperature_metric_edge(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_temp_metric \n")
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.EDGE, amdsmi.AmdSmiTemperatureMetric.CURRENT)
            print("  Current temperature for EDGE is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.EDGE, amdsmi.AmdSmiTemperatureMetric.CRITICAL)
            print("  Limit (critical) temperature for EDGE is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.EDGE, amdsmi.AmdSmiTemperatureMetric.EMERGENCY)
            print("  Shutdown (emergency) temperature for EDGE is: {}".format(
                temperature_measure))
        print()
        self.tearDown()

    def test_temperature_metric_plx(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_temp_metric \n")
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.PLX, amdsmi.AmdSmiTemperatureMetric.CURRENT)
            print("  Current temperature for PLX is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.PLX, amdsmi.AmdSmiTemperatureMetric.CRITICAL)
            print("  Limit (critical) temperature for PLX is: {}".format(
                temperature_measure))
            temperature_measure = amdsmi.amdsmi_get_temp_metric(
                processors[i], amdsmi.AmdSmiTemperatureType.PLX, amdsmi.AmdSmiTemperatureMetric.EMERGENCY)
            print("  Shutdown (emergency) temperature for PLX is: {}".format(
                temperature_measure))
        print()
        self.tearDown()

    # AmdSmiTemperatureType.HBM_0, HBM_1, HBM_2, HBM_3 are not supported in Navi2x, Navi3x, MI210, MI300A
    @handle_exceptions
    def test_temperature_metric_hbm(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        temp_types = {
            "HBM_0": amdsmi.AmdSmiTemperatureType.HBM_0,
            "HBM_1": amdsmi.AmdSmiTemperatureType.HBM_1,
            "HBM_2": amdsmi.AmdSmiTemperatureType.HBM_2,
            "HBM_3": amdsmi.AmdSmiTemperatureType.HBM_3,
        }
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_temp_metric \n")
            for temp_type_name, temp_type_code in temp_types.items():
                temperature_measure = amdsmi.amdsmi_get_temp_metric(
                    processors[i], temp_type_code, amdsmi.AmdSmiTemperatureMetric.CURRENT)
                print("  Current temperature for {} is: {}".format(
                    temp_type_name, temperature_measure))
                temperature_measure = amdsmi.amdsmi_get_temp_metric(
                    processors[i], temp_type_code, amdsmi.AmdSmiTemperatureMetric.CRITICAL)
                print("  Limit (critical) temperature for {} is: {}".format(
                    temp_type_name, temperature_measure))
                temperature_measure = amdsmi.amdsmi_get_temp_metric(
                    processors[i], temp_type_code, amdsmi.AmdSmiTemperatureMetric.EMERGENCY)
                print("  Shutdown (emergency) temperature for {} is: {}".format(
                    temp_type_name, temperature_measure))
        print()
        self.tearDown()

    def test_utilization_count(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_utilization_count \n")
            utilization_counter_types = [
                amdsmi.AmdSmiUtilizationCounterType.COARSE_GRAIN_GFX_ACTIVITY,
                amdsmi.AmdSmiUtilizationCounterType.COARSE_GRAIN_MEM_ACTIVITY,
                amdsmi.AmdSmiUtilizationCounterType.COARSE_DECODER_ACTIVITY
            ]
            utilization_count = amdsmi.amdsmi_get_utilization_count(
                processors[i], utilization_counter_types)
            print("  Timestamp: {}".format(
                utilization_count[0]['timestamp']))
            print("  Utilization count for {} is: {}".format(
                utilization_count[1]['type'], utilization_count[1]['value']))
            print("  Utilization count for {} is: {}".format(
                utilization_count[2]['type'], utilization_count[2]['value']))
            print("  Utilization count for {} is: {}".format(
                utilization_count[3]['type'], utilization_count[3]['value']))
            self.assertLessEqual(len(processors), 32)
            print()
            utilization_counter_types = [
                amdsmi.AmdSmiUtilizationCounterType.FINE_GRAIN_GFX_ACTIVITY,
                amdsmi.AmdSmiUtilizationCounterType.FINE_GRAIN_MEM_ACTIVITY,
                amdsmi.AmdSmiUtilizationCounterType.FINE_DECODER_ACTIVITY
            ]
            utilization_count = amdsmi.amdsmi_get_utilization_count(
                processors[i], utilization_counter_types)
            print("  Timestamp: {}".format(
                utilization_count[0]['timestamp']))
            print("  Utilization count for {} is: {}".format(
                utilization_count[1]['type'], utilization_count[1]['value']))
            print("  Utilization count for {} is: {}".format(
                utilization_count[2]['type'], utilization_count[2]['value']))
            print("  Utilization count for {} is: {}".format(
                utilization_count[3]['type'], utilization_count[3]['value']))
        print()
        self.tearDown()

    def test_vbios_info(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_vbios_info \n")
            vbios_info = amdsmi.amdsmi_get_gpu_vbios_info(processors[i])
            print("  vbios_info['part_number'] is: {}".format(
                vbios_info['part_number']))
            print("  vbios_info['build_date'] is: {}".format(
                vbios_info['build_date']))
            print("  vbios_info['name'] is: {}".format(
                vbios_info['name']))
            print("  vbios_info['version'] is: {}".format(
                vbios_info['version']))
        print()
        self.tearDown()

    def test_vendor_name(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_vendor_name \n")
            vendor_name = amdsmi.amdsmi_get_gpu_vendor_name(processors[i])
            print("  Vendor name is: {}".format(vendor_name))
        print()
        self.tearDown()

    # @unittest.SkipTest
    @handle_exceptions
    def test_accelerator_partition_profile(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_gpu_accelerator_partition_profile \n")
            accelerator_partition = amdsmi.amdsmi_get_gpu_accelerator_partition_profile(processors[i])
            print("  Current partition id: {}".format(
                accelerator_partition['partition_id']))
        print()
        self.tearDown()

    # amdsmi_get_violation_status is only supported on MI300+ ASICs
    # We should expect a not supported status for Navi / MI100 / MI2x ASICs
    @handle_exceptions
    def test_get_violation_status(self):
        self.setUp()
        processors = amdsmi.amdsmi_get_processor_handles()
        self.assertGreaterEqual(len(processors), 1)
        self.assertLessEqual(len(processors), 32)
        for i in range(0, len(processors)):
            bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
            print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
            print("\n###Test amdsmi_get_violation_status \n")

            violation_status = amdsmi.amdsmi_get_violation_status(processors[i])
            print("  Reference Timestamp: {}".format(
                violation_status['reference_timestamp']))
            print("  Violation Timestamp: {}".format(
                violation_status['violation_timestamp']))

            print(" Current Prochot Thrm Accumulated (Count): {}".format(
                violation_status['acc_prochot_thrm']))
            print(" Current PVIOL (acc_ppt_pwr) Accumulated (Count): {}".format(
                violation_status['acc_ppt_pwr']))
            print(" Current TVIOL (acc_socket_thrm) Accumulated (Count): {}".format(
                violation_status['acc_socket_thrm']))
            print(" Current VR_THRM Accumulated (Count): {}".format(
                violation_status['acc_vr_thrm']))
            print(" Current HBM Thrm Accumulated (Count): {}".format(
                violation_status['acc_hbm_thrm']))

            print(" Prochot Thrm Violation (%): {}".format(
                violation_status['per_prochot_thrm']))
            print(" PVIOL (per_ppt_pwr) (%): {}".format(
                violation_status['per_ppt_pwr']))
            print(" TVIOL (per_socket_thrm) (%): {}".format(
                violation_status['per_socket_thrm']))
            print(" VR_THRM Violation (%): {}".format(
                violation_status['per_vr_thrm']))
            print(" HBM Thrm Violation (%): {}".format(
                violation_status['per_hbm_thrm']))

            print(" Prochot Thrm Violation (bool): {}".format(
                violation_status['active_prochot_thrm']))
            print(" PVIOL (active_ppt_pwr) (bool): {}".format(
                violation_status['active_ppt_pwr']))
            print(" TVIOL (active_socket_thrm) (bool): {}".format(
                violation_status['active_socket_thrm']))
            print(" VR_THRM Violation (bool): {}".format(
                violation_status['active_vr_thrm']))
            print(" HBM Thrm Violation (bool): {}".format(
                violation_status['active_hbm_thrm']))
        print()
        self.tearDown()


    def test_walkthrough(self):
        print("\n\n#######################################################################")
        print("========> test_walkthrough start <========\n")
        self.test_asic_kfd_info()
        self.test_power_info()
        self.test_vbios_info()
        self.test_board_info()
        self.test_fw_info()
        self.test_driver_info()
        print("\n========> test_walkthrough end <========")
        print("#######################################################################\n")

    # Unstable on workstation cards
    # @handle_exceptions
    # def test_walkthrough_multiprocess(self):
    #     print("\n\n========> test_walkthrough_multiprocess start <========\n")
    #     processors = amdsmi.amdsmi_get_processor_handles()
    #     self.assertGreaterEqual(len(processors), 1)
    #     self.assertLessEqual(len(processors), 32)
    #     p0 = multiprocessing.Process(target=walk_through, args=[self])
    #     p1 = multiprocessing.Process(target=walk_through, args=[self])
    #     p2 = multiprocessing.Process(target=walk_through, args=[self])
    #     p3 = multiprocessing.Process(target=walk_through, args=[self])
    #     p0.start()
    #     p1.start()
    #     p2.start()
    #     p3.start()
    #     p0.join()
    #     p1.join()
    #     p2.join()
    #     p3.join()
    #     print("\n========> test_walkthrough_multiprocess end <========\n")

    # Unstable on workstation cards
    # @handle_exceptions
    # def test_walkthrough_multithread(self):
    #     print("\n\n========> test_walkthrough_multithread start <========\n")
    #     processors = amdsmi.amdsmi_get_processor_handles()
    #     self.assertGreaterEqual(len(processors), 1)
    #     self.assertLessEqual(len(processors), 32)
    #     t0 = threading.Thread(target=walk_through, args=[self])
    #     t1 = threading.Thread(target=walk_through, args=[self])
    #     t2 = threading.Thread(target=walk_through, args=[self])
    #     t3 = threading.Thread(target=walk_through, args=[self])
    #     t0.start()
    #     t1.start()
    #     t2.start()
    #     t3.start()
    #     t0.join()
    #     t1.join()
    #     t2.join()
    #     t3.join()
    #     print("\n========> test_walkthrough_multithread end <========\n")

    # # Unstable - do not run
    # @handle_exceptions
    # def test_z_gpureset_asicinfo_multithread(self):
    #     def get_asic_info(processor):
    #         print("\n###Test amdsmi_get_gpu_asic_info \n")
    #         asic_info = amdsmi.amdsmi_get_gpu_asic_info(processor)
    #         print("  asic_info['market_name'] is: {}".format(
    #             asic_info['market_name']))
    #         print("  asic_info['vendor_id'] is: {}".format(
    #             asic_info['vendor_id']))
    #         print("  asic_info['vendor_name'] is: {}".format(
    #             asic_info['vendor_name']))
    #         print("  asic_info['device_id'] is: {}".format(
    #             asic_info['device_id']))
    #         print("  asic_info['rev_id'] is: {}".format(
    #             asic_info['rev_id']))
    #         print("  asic_info['asic_serial'] is: {}".format(
    #             asic_info['asic_serial']))
    #         print("  asic_info['oam_id'] is: {}\n".format(
    #             asic_info['oam_id']))
    #     def gpu_reset(processor):
    #         print("\n###Test amdsmi_reset_gpu \n")
    #         amdsmi.amdsmi_reset_gpu(processor)
    #         print("  GPU reset completed.\n")
    #     print("\n\n========> test_z_gpureset_asicinfo_multithread start <========\n")
    #     processors = amdsmi.amdsmi_get_processor_handles()
    #     self.assertGreaterEqual(len(processors), 1)
    #     self.assertLessEqual(len(processors), 32)
    #     for i in range(0, len(processors)):
    #         bdf = amdsmi.amdsmi_get_gpu_device_bdf(processors[i])
    #         print("\n\n###Test Processor {}, bdf: {}".format(i, bdf))
    #         t0 = threading.Thread(target=get_asic_info, args=[processors[i]])
    #         t1 = threading.Thread(target=gpu_reset, args=[processors[i]])
    #         # t2 = threading.Thread(target=walk_through, args=[self])
    #         # t3 = threading.Thread(target=walk_through, args=[self])
    #         t0.start()
    #         t1.start()
    #         # t2.start()
    #         # t3.start()
    #         t0.join()
    #         t1.join()
    #         # t2.join()
    #         # t3.join()
    #     print("\n========> test_z_gpureset_asicinfo_multithread end <========\n")

if __name__ == '__main__':
    unittest.main()