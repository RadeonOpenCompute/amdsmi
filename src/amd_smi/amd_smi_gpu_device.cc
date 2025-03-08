/*
 * Copyright (c) Advanced Micro Devices, Inc. All rights reserved.
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

#include "amd_smi/impl/amd_smi_gpu_device.h"
#include "amd_smi/impl/amd_smi_common.h"
#include "amd_smi/impl/fdinfo.h"
#include "rocm_smi/rocm_smi_kfd.h"
#include "rocm_smi/rocm_smi_utils.h"

#include <functional>
#include <map>
#include <memory>
#include <unordered_set>
#include <dirent.h>
#include <sys/types.h>

namespace amd {
namespace smi {

uint32_t AMDSmiGPUDevice::get_gpu_id() const {
    return gpu_id_;
}

uint32_t AMDSmiGPUDevice::get_gpu_fd() const {
    return fd_;
}

std::string& AMDSmiGPUDevice::get_gpu_path() {
    return path_;
}

amdsmi_bdf_t AMDSmiGPUDevice::get_bdf() {
    return bdf_;
}

uint32_t AMDSmiGPUDevice::get_vendor_id() {
    return vendor_id_;
}

amdsmi_status_t AMDSmiGPUDevice::get_drm_data() {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    std::string path;
    amdsmi_bdf_t bdf;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;
    ret = drm_.get_drm_path_by_index(gpu_id_, &path);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;
    ret = drm_.get_bdf_by_index(gpu_id_, &bdf);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    bdf_ = bdf, path_ = path, fd_ = fd;
    vendor_id_ = drm_.get_vendor_id();

    return AMDSMI_STATUS_SUCCESS;
}

pthread_mutex_t* AMDSmiGPUDevice::get_mutex() {
    return amd::smi::GetMutex(gpu_id_);
}

amdsmi_status_t AMDSmiGPUDevice::amdgpu_query_info(unsigned info_id,
                    unsigned size, void *value) const {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    return drm_.amdgpu_query_info(fd, info_id, size, value);
}

amdsmi_status_t AMDSmiGPUDevice::amdgpu_query_driver_name(std::string& name) const {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    return drm_.amdgpu_query_driver_name(fd, name);
}

amdsmi_status_t AMDSmiGPUDevice::amdgpu_query_driver_date(std::string& date) const {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    return drm_.amdgpu_query_driver_date(fd, date);
}

amdsmi_status_t AMDSmiGPUDevice::amdgpu_query_hw_ip(unsigned info_id,
            unsigned hw_ip_type, unsigned size, void *value) const {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    return drm_.amdgpu_query_hw_ip(fd, info_id, hw_ip_type, size, value);
}

amdsmi_status_t AMDSmiGPUDevice::amdgpu_query_fw(unsigned info_id,
        unsigned fw_type, unsigned size, void *value) const {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    return drm_.amdgpu_query_fw(fd, info_id, fw_type, size, value);
}

amdsmi_status_t AMDSmiGPUDevice::amdgpu_query_vbios(void *info) const {
    amdsmi_status_t ret;
    uint32_t fd = 0;
    ret = drm_.get_drm_fd_by_index(gpu_id_, &fd);
    if (ret != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

    return drm_.amdgpu_query_vbios(fd, info);
}


int32_t AMDSmiGPUDevice::get_compute_process_list_impl(GPUComputeProcessList_t& compute_process_list,
                                                       ComputeProcessListType_t list_type)
{

    /**
     *  Clear the compute_process_list before starting.
     */
    compute_process_list.clear();

    /**
     *  The first call to GetProcessInfo() helps to find the size it needs,
     *  so we can create a tailored size list.
     */
    auto status_code(rsmi_status_t::RSMI_STATUS_SUCCESS);
    auto list_process_running_size = uint32_t(0);
    auto list_process_allocation_size = uint32_t(0);

    status_code = rsmi_compute_process_info_get(nullptr, &list_process_running_size);
    if ((status_code != rsmi_status_t::RSMI_STATUS_SUCCESS) || (list_process_running_size <= 0)) {
        return status_code;
    }

    /**
     *  The second call to GetProcessInfo() helps to set proper sizes for both,
     *  the raw array of processes (amdsmi_process_info_t) and list of processes (amdsmi_proc_info_t).
     */
    using RsmiDeviceList_t = uint32_t[];
    using RsmiProcessList_t = rsmi_process_info_t[];
    std::unique_ptr<RsmiProcessList_t> list_all_processes_ptr = std::make_unique<RsmiProcessList_t>(list_process_running_size);

    list_process_allocation_size = list_process_running_size;
    status_code = rsmi_compute_process_info_get(list_all_processes_ptr.get(), &list_process_allocation_size);
    if (status_code) {
        return status_code;
    }

    // Restore the original size to read
    list_process_running_size = list_process_allocation_size;
    if (list_process_running_size <= 0) {
        return rsmi_status_t::RSMI_STATUS_NOT_FOUND;
    }


    /**
     *  Setup for the cases where the process list is by device.
     */
    auto list_device_running_size = uint32_t(0);
    auto list_device_allocation_size = uint32_t(0);
    status_code = rsmi_num_monitor_devices(&list_device_running_size);
    if ((status_code != rsmi_status_t::RSMI_STATUS_SUCCESS) || (list_device_running_size <= 0)) {
        return status_code;
    }


    /**
     * Complete the process information
     */
    auto get_process_info = [&](const rsmi_process_info_t& rsmi_proc_info, amdsmi_proc_info_t& asmi_proc_info) {
        auto status_code = gpuvsmi_get_pid_info(get_bdf(), rsmi_proc_info.process_id, asmi_proc_info);
        // If we cannot get the info from sysfs, save the minimum info
        if (status_code != amdsmi_status_t::AMDSMI_STATUS_SUCCESS) {
            asmi_proc_info.pid = rsmi_proc_info.process_id;
            asmi_proc_info.memory_usage.vram_mem = rsmi_proc_info.vram_usage;
        }

        return status_code;
    };

    /**
     * Get process information
     */
    auto update_list_by_running_process = [&](const uint32_t process_id) {
        auto status_result(true);
        rsmi_process_info_t rsmi_proc_info{};
        auto status_code = rsmi_compute_process_info_by_pid_get(process_id, &rsmi_proc_info);
        if (status_code != rsmi_status_t::RSMI_STATUS_SUCCESS) {
            status_result = false;
            return status_result;
        }

        amdsmi_proc_info_t tmp_asmi_proc_info{};
        get_process_info(rsmi_proc_info, tmp_asmi_proc_info);
        compute_process_list.emplace(process_id, tmp_asmi_proc_info);

        return status_result;
    };


    /**
     *  Devices used by a process.
     */
    auto update_list_by_running_device = [&](const uint32_t process_id,
                                             const uint32_t proc_addr_id) {
        // Get all devices running this process
        auto status_result(true);
        std::unique_ptr<RsmiDeviceList_t> list_device_ptr = std::make_unique<RsmiDeviceList_t>(list_device_running_size);
        list_device_allocation_size = list_device_running_size;
        auto status_code = rsmi_compute_process_gpus_get(process_id, list_device_ptr.get(), &list_device_allocation_size);
        if (status_code != rsmi_status_t::RSMI_STATUS_SUCCESS) {
            status_result = false;
            return status_result;
        }

        for (auto device_idx = uint32_t(0); device_idx < list_device_allocation_size; ++device_idx) {
            // Is this device running this process?
            if (list_device_ptr[device_idx] == get_gpu_id()) {
                rsmi_process_info_t rsmi_dev_proc_info{};
                // TODO remove pasid Not working in ROCm 6.4+, deprecating in 7.0
                auto status_code = rsmi_compute_process_info_by_device_get(process_id, list_device_ptr[device_idx], &rsmi_dev_proc_info);
                if ((status_code == rsmi_status_t::RSMI_STATUS_SUCCESS) &&
                    ((rsmi_dev_proc_info.process_id == process_id) && (rsmi_dev_proc_info.pasid == proc_addr_id))) {
                    amdsmi_proc_info_t tmp_asmi_proc_info{};
                    get_process_info(rsmi_dev_proc_info, tmp_asmi_proc_info);
                    compute_process_list.emplace(process_id, tmp_asmi_proc_info);
                }
            }
        }

        return status_result;
    };


    /**
     *  Transfer/Save the ones linked to this device.
     */
    compute_process_list.clear();
    for (auto process_idx = uint32_t(0); process_idx < list_process_running_size; ++process_idx) {
        if (list_type == ComputeProcessListType_t::kAllProcesses) {
            if (update_list_by_running_process(list_all_processes_ptr[process_idx].process_id)) {
            }
        }

        if (list_type == ComputeProcessListType_t::kAllProcessesOnDevice) {
            if (update_list_by_running_device(list_all_processes_ptr[process_idx].process_id,
                                              list_all_processes_ptr[process_idx].pasid)) {
            }
        }
    }

    return status_code;
}

const GPUComputeProcessList_t& AMDSmiGPUDevice::amdgpu_get_compute_process_list(ComputeProcessListType_t list_type)
{
    auto error_code = get_compute_process_list_impl(compute_process_list_, list_type);
    if (error_code) {
        compute_process_list_.clear();
    }

    return compute_process_list_;
}

// Convert `amdsmi_bdf_t` to a PCI BDF string
std::string AMDSmiGPUDevice::bdf_to_string() const {
    std::ostringstream oss;
    oss << std::setfill('0') << std::hex      // Use hexadecimal formatting
        << std::setw(4) << bdf_.domain_number << ":"  // Domain (4 digits)
        << std::setw(2) << static_cast<int>(bdf_.bus_number) << ":"  // Bus (2 digits)
        << std::setw(2) << static_cast<int>(bdf_.device_number) << "."  // Device (2 digits)
        << static_cast<int>(bdf_.function_number);  // Function (1 digit)
    return oss.str();
}


uint32_t AMDSmiGPUDevice::get_card_from_bdf() const {
    const std::string drm_path = "/sys/class/drm/";

    DIR* dir = opendir(drm_path.c_str());
    if (!dir) {
        return std::numeric_limits<uint32_t>::max();
    }

    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        std::string device_name = entry->d_name;

        // Check if the entry starts with "card"
        if (device_name.find("card") == 0) {
            const std::string card_path = drm_path + device_name + "/device";

            // Open the uevent file for the device
            std::ifstream uevent_file(card_path + "/uevent");
            if (!uevent_file) {
                continue;  // Skip if the file is not found
            }

            std::string line;
            while (std::getline(uevent_file, line)) {
                // Check for the PCI_SLOT_NAME and if it contains the BDF
                if (line.rfind("PCI_SLOT_NAME", 0) == 0 && line.find(bdf_to_string()) != std::string::npos) {
                    closedir(dir);
                    return std::stoi(device_name.substr(4));  // Convert extracted number to int
                }
            }
        }
    }

    closedir(dir);
    return std::numeric_limits<uint32_t>::max();  // Return -1 if no matching card is found
}

uint32_t AMDSmiGPUDevice::get_render_id() const {
    const std::string drm_path = "/sys/class/drm/";

    DIR* dir = opendir(drm_path.c_str());
    if (!dir) {
        return std::numeric_limits<uint32_t>::max();
    }

    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        std::string device_name = entry->d_name;

        // Check if the entry starts with "renderD"
        if (device_name.find("renderD") == 0) {
            const std::string render_path = drm_path + device_name + "/device";

            // Open the uevent file for the device
            std::ifstream uevent_file(render_path + "/uevent");
            if (!uevent_file) {
                continue;  // Skip if the file is not found
            }

            std::string line;
            while (std::getline(uevent_file, line)) {
                // Check for the PCI_SLOT_NAME and if it contains the BDF
                if (line.rfind("PCI_SLOT_NAME", 0) == 0 && line.find(bdf_to_string()) != std::string::npos) {
                    closedir(dir);
                    return std::stoi(device_name.substr(7));  // Extract only the number after "renderD"
                }
            }
        }
    }

    closedir(dir);
    return std::numeric_limits<uint32_t>::max();  // Return -1 if no matching render ID is found
}


}  // namespace smi
}  // namespace amd

