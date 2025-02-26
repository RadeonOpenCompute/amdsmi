/*
 * Copyright (c) Broadcom Inc All Rights Reserved.
 *
 *  Developed by:
 *            Broadcom Inc
 *
 *            www.broadcom.com
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <iostream>
#include <vector>
#include "amd_smi/amdsmi.h"
#define CHK_AMDSMI_RET(RET) \
{ \
    if (RET != AMDSMI_STATUS_SUCCESS) { \
        const char *err_str; \
        std::cout << "AMDSMI call returned " << RET << " at line " \
                    << __LINE__ << std::endl; \
        amdsmi_status_code_to_string(RET, &err_str); \
        std::cout << err_str << std::endl; \
        return RET; \
    } \
}


int main(int argc, char **argv) {
    amdsmi_status_t ret;
    uint32_t socket_count = 0;

    // Initialize amdsmi for AMD CPUs
    ret = amdsmi_init(AMDSMI_INIT_AMD_GPUS);

    ret = amdsmi_get_socket_handles(&socket_count, nullptr);

    // Allocate the memory for the sockets
    std::vector<amdsmi_socket_handle> sockets(socket_count);

    // Get the sockets of the system
    ret = amdsmi_get_socket_handles(&socket_count, &sockets[0]);

    std::cout << "Total Socket: " << socket_count << std::endl;

    // For each socket, get cpus
    for (uint32_t i = 0; i < socket_count; i++) {

        // Get the device count available for the socket.
        uint32_t device_count = 0;
        uint32_t tmp_device_count = 0;
        bool isGPU, isNIC, isSWITCH;
        ret = amdsmi_get_processor_handles_by_type(sockets[i], AMDSMI_PROCESSOR_TYPE_AMD_GPU, nullptr, &tmp_device_count);
        CHK_AMDSMI_RET(ret)

        // Allocate the memory for the device handlers on the socket
        
        if (tmp_device_count == 0) { //it could be BRCM NIC device
          ret = amdsmi_get_processor_handles_by_type(sockets[i], AMDSMI_PROCESSOR_TYPE_BRCM_NIC, nullptr, &tmp_device_count);
          device_count = tmp_device_count;
          isNIC = true;
          CHK_AMDSMI_RET(ret)
        } else {
          device_count = tmp_device_count;
          isGPU = true;
        }

        if (tmp_device_count == 0) {  // it could be BRCM SWITCH device
          ret = amdsmi_get_processor_handles_by_type(sockets[i], AMDSMI_PROCESSOR_TYPE_BRCM_SWITCH, nullptr,
                                                     &tmp_device_count);
          device_count = tmp_device_count;
          isNIC = false;
          isGPU = false;
          isSWITCH = true;
          CHK_AMDSMI_RET(ret)
        }

        // Allocate the memory for the device handlers on the socket
        std::vector<amdsmi_processor_handle> processor_handles(device_count);

        if (isNIC) {
          ret = amdsmi_get_processor_handles_by_type(sockets[i], AMDSMI_PROCESSOR_TYPE_BRCM_NIC, &processor_handles[0], &device_count);
          CHK_AMDSMI_RET(ret)
        } else if (isGPU) {
          ret = amdsmi_get_processor_handles_by_type(sockets[i], AMDSMI_PROCESSOR_TYPE_AMD_GPU, &processor_handles[0], &device_count);
          CHK_AMDSMI_RET(ret)
        } else if (isSWITCH) {
          ret = amdsmi_get_processor_handles_by_type(sockets[i], AMDSMI_PROCESSOR_TYPE_BRCM_SWITCH, &processor_handles[0], &device_count);
          CHK_AMDSMI_RET(ret)
        } else {
          printf("\n Unknown device as part of discovered list. Exiting! \n");
          ret = amdsmi_shut_down();
          CHK_AMDSMI_RET(ret)
          return 0;
        }
 
        for (uint32_t j = 0; j < device_count; j++) {

            processor_type_t processor_type = {};
            ret = amdsmi_get_processor_type(processor_handles[j], &processor_type);
            CHK_AMDSMI_RET(ret)

            amdsmi_bdf_t bdf = {};

            if (isNIC) {
                amdsmi_nic_temperature_metric_t info;
                ret = amdsmi_get_nic_temp_info(processor_handles[j], &info);
                printf("nic_temp_crit: %d\n", info.nic_temp_crit);
                printf("nic_temp_emergency: %d\n", info.nic_temp_emergency);
                printf("nic_temp_input: %d\n", info.nic_temp_input);
                printf("nic_temp_max: %d\n", info.nic_temp_max);
                printf("nic_temp_shutdown: %d\n", info.nic_temp_shutdown);

                ret = amdsmi_get_nic_device_bdf(processor_handles[j], &bdf);
            }
            else if (isGPU) {
                ret = amdsmi_get_gpu_device_bdf(processor_handles[j], &bdf);
            } 
            else if (isSWITCH) {
              ret = amdsmi_get_switch_device_bdf(processor_handles[j], &bdf);
            }
            std::string pType = "";
            if (processor_type == AMDSMI_PROCESSOR_TYPE_AMD_GPU) {
                pType= "AMD_GPU";
            }
            else if(processor_type == AMDSMI_PROCESSOR_TYPE_BRCM_NIC) {
                pType = "BRCM_NIC";
            }
            else if (processor_type == AMDSMI_PROCESSOR_TYPE_BRCM_SWITCH) {
              pType = "BRCM_SWITCH";
            }
            unsigned int uuid_length = AMDSMI_GPU_UUID_SIZE;
            char uuid[AMDSMI_GPU_UUID_SIZE];
            if (isNIC) {
                ret = amdsmi_get_nic_device_uuid(processor_handles[j], &uuid_length, uuid);
            } 
            else if (isGPU) {
                ret = amdsmi_get_gpu_device_uuid(processor_handles[j], &uuid_length, uuid);
            } 
            else if (isSWITCH) {
              ret = amdsmi_get_switch_device_uuid(processor_handles[j], &uuid_length, uuid);
            }
            CHK_AMDSMI_RET(ret)

            if(ret != AMDSMI_STATUS_SUCCESS)
                        std::cout<<"Failed to get bdf"<<"["<<j<<"] , Err["<<ret<<"] "<< std::endl;
            else
                printf("\tDevice[%d] \n\ttype[%s] \n\tBDF %04lx:%02x:%02x.%d \n\tUUID:%s\n\n", i,pType.c_str(), 
                    bdf.domain_number,
                    bdf.bus_number,
                    bdf.device_number,
                    bdf.function_number,
                    uuid);
                std::cout<<std::endl;
          }
      }
   
    ret = amdsmi_shut_down();
    CHK_AMDSMI_RET(ret)

    return 0;
}
