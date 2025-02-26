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
#include <regex>
#include "amd_smi/impl/amd_smi_no_drm_switch.h"
#include "amd_smi/impl/amd_smi_common.h"
#include "amd_smi/impl/amd_smi_utils.h"
#include "amd_smi/impl/amd_smi_lspci_commands.h"
#include "rocm_smi/rocm_smi.h"
#include "rocm_smi/rocm_smi_main.h"

namespace amd {
namespace smi {



amdsmi_status_t AMDSmiNoDrmSwitch::init() {

    amd::smi::RocmSMI& smi = amd::smi::RocmSMI::getInstance();
    auto devices = smi.switch_devices();

    bool has_valid_fds = false;
    for (uint32_t i=0; i < devices.size(); i++) {
        auto rocm_smi_device = devices[i];
        const std::string switch_host_folder = "/sys/class/scsi_host/host" + std::to_string(rocm_smi_device->index());
        std::string switch_dev_folder = switch_host_folder;
        std::vector<char> buf(400);
        ssize_t len;

        do {
          buf.resize(buf.size() + 100);
          len = ::readlink(switch_dev_folder.c_str(), &(buf[0]), buf.size());
        } while (buf.size() == len);

        if (len > 0) {
          buf[len] = '\0';
          switch_dev_folder = std::string(&(buf[0]));
          std::string suffixDel = "host" + std::to_string(rocm_smi_device->index()) +
                                  "/scsi_host/" + "host" +
                                  std::to_string(rocm_smi_device->index()) + "/";
          switch_dev_folder.erase(switch_dev_folder.length() - suffixDel.length());

          auto first = switch_dev_folder.begin();
          auto end = switch_dev_folder.begin() + switch_dev_folder.length() - 12;  // 12 characters. For example: "0000:45:00.0"
          switch_dev_folder.erase(first, end);

          std::string prefixAdd = "/sys/bus/pci/devices/";
          switch_dev_folder = prefixAdd.append(switch_dev_folder);
        }

        std::ostringstream ss;
        std::string vend_path = switch_dev_folder + "/vendor";
        std::string ldev_path = switch_dev_folder + "/device";

        if (FileExists(vend_path.c_str()) && FileExists(ldev_path.c_str())) {
          std::ifstream vfs, dfs;
          vfs.open(vend_path);
          dfs.open(ldev_path);

          if (vfs.is_open() && dfs.is_open()) {
            uint32_t vendor_id;
            uint32_t dev_id;

            vfs >> std::hex >> vendor_id;
            dfs >> std::hex >> dev_id;

            vfs.close();
            dfs.close();

            if (vendor_id == 0x1000 && dev_id == 0x00b2) {
              device_paths_.push_back(switch_dev_folder);
              host_paths_.push_back(switch_host_folder);
              has_valid_fds = true;

              uint64_t bdfid = 0;
              rsmi_status_t ret = rsmi_switch_dev_pci_id_get(i, &bdfid);
              if (ret != RSMI_STATUS_SUCCESS) {
                continue;
              }
              amdsmi_bdf_t bdf = {};
              bdf.function_number = bdfid & 0x7;
              bdf.device_number = (bdfid >> 3) & 0x1f;
              bdf.bus_number = (bdfid >> 8) & 0xff;
              bdf.domain_number = (bdfid >> 32) & 0xffffffff;
              no_drm_bdfs_.push_back(bdf);
            }
          }
        }
    }

    // cannot find any valid fds.
    if (!has_valid_fds) {
        no_drm_bdfs_.clear();
        return AMDSMI_STATUS_INIT_ERROR;
    }

    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmSwitch::cleanup() {
    device_paths_.clear();
    host_paths_.clear();
    no_drm_bdfs_.clear();
    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmSwitch::amd_query_switch_link( std::string devicePath,
        amdsmi_brcm_link_metric_t &info) {
 
  std::string current_speed = "current_link_speed";
  std::string max_speed = "max_link_speed";
  std::string current_width = "current_link_width";
  std::string max_width = "max_link_width";

  info.current_link_speed = smi_brcm_get_value_u32(devicePath, current_speed);
  info.max_link_speed = smi_brcm_get_value_u32(devicePath, max_speed);
  info.current_link_width = smi_brcm_get_value_u32(devicePath, current_width);
  info.max_link_width = smi_brcm_get_value_u32(devicePath, max_width);
  
}

amdsmi_status_t AMDSmiNoDrmSwitch::amd_query_switch_uuid(std::string bdfStr, std::string& serial) {

  get_lspci_device_data(bdfStr, switchSerialNumber, serial);

  return AMDSMI_STATUS_SUCCESS;
}


amdsmi_status_t AMDSmiNoDrmSwitch::get_bdf_by_index(uint32_t switch_index, amdsmi_bdf_t *bdf_info) const {
    if (switch_index + 1 > no_drm_bdfs_.size()) return AMDSMI_STATUS_NOT_SUPPORTED;
    *bdf_info = no_drm_bdfs_[switch_index];
    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmSwitch::get_device_path_by_index(uint32_t switch_index, std::string *device_path) const {
    if (switch_index + 1 > device_paths_.size()) return AMDSMI_STATUS_NOT_SUPPORTED;
    *device_path = device_paths_[switch_index];
    return AMDSMI_STATUS_SUCCESS;
}

amdsmi_status_t AMDSmiNoDrmSwitch::get_hwmon_path_by_index(uint32_t switch_index, std::string *hwm_path) const {
    if (switch_index + 1 > host_paths_.size()) return AMDSMI_STATUS_NOT_SUPPORTED;
    *hwm_path = host_paths_[switch_index];
    return AMDSMI_STATUS_SUCCESS;
}

std::vector<std::string>& AMDSmiNoDrmSwitch::get_device_paths() { return device_paths_; }
std::vector<std::string> &AMDSmiNoDrmSwitch::get_hwmon_paths() { return host_paths_; }

bool AMDSmiNoDrmSwitch::check_if_no_drm_is_supported() { return true; }

std::vector<amdsmi_bdf_t> AMDSmiNoDrmSwitch::get_bdfs() {
    return no_drm_bdfs_;
}


}  // namespace smi
}  // namespace amd

