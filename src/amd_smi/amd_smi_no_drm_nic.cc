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
 
#include <sys/types.h>
#include <dirent.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include "amd_smi/impl/amd_smi_no_drm_nic.h"
#include "amd_smi/impl/amd_smi_common.h"
#include "amd_smi/impl/amd_smi_utils.h"
#include "rocm_smi/rocm_smi.h"
#include "rocm_smi/rocm_smi_main.h"

namespace amd {
namespace smi {

amdsmi_status_t AMDSmiNoDrmNIC::init() {

    amd::smi::RocmSMI& smi = amd::smi::RocmSMI::getInstance();
    auto devices = smi.nic_devices();

    bool has_valid_hw_mon = false;
    for (uint32_t i=0; i < devices.size(); i++) {
      auto rocm_smi_device = devices[i];
      uint64_t bdfid = rocm_smi_device->bdfid();
      amdsmi_bdf_t bdf = {};
      bdf.function_number = bdfid & 0x7;
      bdf.device_number = (bdfid >> 3) & 0x1f;
      bdf.bus_number = (bdfid >> 8) & 0xff;
      bdf.domain_number = (bdfid >> 32) & 0xffffffff;
      no_drm_bdfs_.push_back(bdf);

      const std::string nic_dev_folder = rocm_smi_device->path() + "/device";
      device_paths_.push_back(nic_dev_folder);
      auto nic_dev_dir = opendir(std::string((nic_dev_folder + "/hwmon")).c_str());

      if (nic_dev_dir != nullptr) {
        auto dentry = readdir(nic_dev_dir);
        while (dentry != nullptr) {
          if (memcmp(dentry->d_name, "hwmon", strlen("hwmon")) == 0) {
            if ((strcmp(dentry->d_name, ".") == 0) || (strcmp(dentry->d_name, "..") == 0)) continue;
              const std::string nic_hw_folder = nic_dev_folder + "/hwmon/" + std::string(dentry->d_name);
              hwmon_paths_.push_back(nic_hw_folder);
              has_valid_hw_mon = true;
              break;
          }
          dentry = readdir(nic_dev_dir);
        }
      }

      // cannot find any valid fds.
      if (!has_valid_hw_mon) {
          hwmon_paths_.push_back("");
      }
    }

    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmNIC::cleanup() {
    device_paths_.clear();
    hwmon_paths_.clear();
    no_drm_bdfs_.clear();
    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmNIC::amd_query_nic_temp(std::string hwmonPath,
        amdsmi_nic_temperature_metric_t &info) {
 
  std::string crit_alarm = "temp1_crit_alarm";
  std::string emergency_alarm = "temp1_emergency_alarm";
  std::string shutdown_alarm = "temp1_shutdown_alarm";
  std::string max_alarm = "temp1_max_alarm";

  std::string nic_crit = "temp1_crit";
  std::string nic_emergency = "temp1_emergency";
  std::string nic_input = "temp1_input";
  std::string nic_max = "temp1_max";
  std::string nic_shutdown = "temp1_shutdown";
  
  info.nic_temp_crit_alarm = smi_brcm_get_value_u32(hwmonPath, crit_alarm);
  info.nic_temp_emergency_alarm = smi_brcm_get_value_u32(hwmonPath, emergency_alarm);
  info.nic_temp_shutdown_alarm = smi_brcm_get_value_u32(hwmonPath, shutdown_alarm);
  info.nic_temp_max_alarm = smi_brcm_get_value_u32(hwmonPath, max_alarm);
  
  info.nic_temp_crit = smi_brcm_get_value_u32(hwmonPath, nic_crit);
  info.nic_temp_emergency = smi_brcm_get_value_u32(hwmonPath, nic_emergency);
  info.nic_temp_input = smi_brcm_get_value_u32(hwmonPath, nic_input);
  info.nic_temp_max = smi_brcm_get_value_u32(hwmonPath, nic_max);
  info.nic_temp_shutdown = smi_brcm_get_value_u32(hwmonPath, nic_shutdown);
  return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmNIC::get_bdf_by_index(uint32_t nic_index, amdsmi_bdf_t *bdf_info) const {
    if (nic_index + 1 > no_drm_bdfs_.size()) return AMDSMI_STATUS_NOT_SUPPORTED;
    *bdf_info = no_drm_bdfs_[nic_index];
    return AMDSMI_STATUS_SUCCESS;
}
amdsmi_status_t AMDSmiNoDrmNIC::get_device_path_by_index(uint32_t nic_index, std::string *device_path) const {
    if (nic_index + 1 > device_paths_.size()) return AMDSMI_STATUS_NOT_SUPPORTED;
    *device_path = device_paths_[nic_index];
    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmNIC::get_hwmon_path_by_index(uint32_t nic_index, std::string *hwm_path) const {
    if (nic_index + 1 > hwmon_paths_.size()) return AMDSMI_STATUS_NOT_SUPPORTED;
    *hwm_path = hwmon_paths_[nic_index];
    return AMDSMI_STATUS_SUCCESS;
}

std::vector<std::string>& AMDSmiNoDrmNIC::get_device_paths() { return device_paths_; }
std::vector<std::string> &AMDSmiNoDrmNIC::get_hwmon_paths() { return hwmon_paths_; }
bool AMDSmiNoDrmNIC::check_if_no_drm_is_supported() { return true; }
std::vector<amdsmi_bdf_t> AMDSmiNoDrmNIC::get_bdfs() { return no_drm_bdfs_; }

amdsmi_status_t AMDSmiNoDrmNIC::amd_query_nic_uuid(std::string devicePath, std::string &version) {
  std::string netPath = devicePath + "/net";
  auto net_node_dir = opendir(netPath.c_str());
  if (net_node_dir == nullptr) {
    return AMDSMI_STATUS_FILE_ERROR;
  }
  auto dentry = readdir(net_node_dir);
  std::string macPath;
  while ((dentry = readdir(net_node_dir)) != nullptr) {
    if ((strcmp(dentry->d_name, ".") == 0) || (strcmp(dentry->d_name, "..") == 0)) {
      continue;
    }
    macPath = netPath + "/" + dentry->d_name;
    std::string macAddress = "address";
    version = smi_brcm_get_value_string(macPath, macAddress);
  }

  return AMDSMI_STATUS_SUCCESS;
}

}  // namespace smi
}  // namespace amd
