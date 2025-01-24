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

#include <fstream>
#include <memory>
#include <regex>


#include "amd_smi/impl/amd_smi_lspci_commands.h"


amdsmi_status_t smi_brcm_execute_cmd_get_data(std::string command, std::string *data) {
    std::string result;
    char buffer[128];

    // Open a pipe to execute the command
    std::shared_ptr<FILE> pipe(popen(command.c_str(), "r"), pclose);
    if (!pipe) {
        return AMDSMI_STATUS_API_FAILED;
    }

    // Read the output of the command into the buffer
    while (fgets(buffer, sizeof(buffer), pipe.get()) != nullptr) {
        result += buffer;
    }

    *data = result;

    return AMDSMI_STATUS_SUCCESS;
}

// Supported lspci -vv command regex match
static const std::map<lspciKeys, const char *> kLspciPatternMap = {
      {switchSerialNumber, R"(Device Serial Number ([\w-]+))"},
   };


amdsmi_status_t get_lspci_device_data(std::string bdfStr, lspciKeys sub_key, std::string &version) {
  std::string lspci_data;
  std::string command = "lspci -s " + bdfStr + " -vv";

  if(smi_brcm_execute_cmd_get_data(command, &lspci_data) != AMDSMI_STATUS_SUCCESS) return AMDSMI_STATUS_NOT_SUPPORTED;

  std::regex pattern(kLspciPatternMap.at(sub_key));
  std::smatch match;

  if(std::regex_search(lspci_data, match, pattern)) {
    if (match.size() > 1) {
      version = match[1].str();
      return AMDSMI_STATUS_SUCCESS;
    }
  }

  return AMDSMI_STATUS_API_FAILED;

}


amdsmi_status_t get_lspci_root_switch(amdsmi_bdf_t devicehBdf, amdsmi_bdf_t *switchBdf) {

  amdsmi_status_t status = AMDSMI_STATUS_SUCCESS;
  std::string lspci_data;

  status = smi_brcm_execute_cmd_get_data("lspci -tvv", &lspci_data);
  std::istringstream lines(lspci_data);

  std::string line, bus;
  uint64_t bus_pos, dev_pos, fun_pos; 
  std::vector<std::string> streamlines;


  while (std::getline(lines, line)) { 
    streamlines.push_back(line);

    std::stringstream ss;
    ss << std::hex << devicehBdf.bus_number;
    if ((line.rfind('[' + ss.str() + ']') != std::string::npos)  | (line.rfind("-[" + ss.str() + '-') != std::string::npos)) {
      while (!streamlines.empty()) {
        if ((streamlines.back()).find(R"(\-)") != std::string::npos) {
        	//Switch tree entered  
          //First find from end the end bus in a line
          bus_pos = (streamlines.back()).rfind("]-");
          if (bus_pos == std::string::npos){
              streamlines.pop_back();
              continue;
          } 

          //Now find from end the 2nd last bus on the line which could be the switch
          bus_pos = (streamlines.back()).rfind("]-", bus_pos-2);
          if (bus_pos == std::string::npos){
              streamlines.pop_back();
              continue;
          }
          bus = (streamlines.back()).substr(bus_pos - 2, 2);

          // Check if the bus address belongs to switch
          status = smi_brcm_execute_cmd_get_data("lspci -s " + bus + ": " + "-tvv", &lspci_data);

          if(lspci_data.find("LSI PCIe Switch management endpoint") != std::string::npos){
              
              //Get device
              dev_pos = (streamlines.back()).find('.', bus_pos);
              if (dev_pos == std::string::npos){
                  streamlines.pop_back();
                  continue;
              }

              //Get function
              fun_pos = (streamlines.back()).find('-', dev_pos);
              if (fun_pos == std::string::npos){
                  streamlines.pop_back();
                  continue;
              }

              try
              {
                  switchBdf->bus_number =  std::stoi(bus, NULL, 16);
                  switchBdf->device_number =  std::stoi((streamlines.back()).substr(dev_pos - 2, 2), NULL, 16);
                  switchBdf->function_number =  std::stoi((streamlines.back()).substr(fun_pos - 1, 1), NULL, 16);
              } 
              catch (const std::invalid_argument& e) {
                  printf("Invalid input: Not a valid hexadecimal string");
              }
              catch (const std::out_of_range& e) {
                  printf("Invalid input: Number out of range");
              }
              
              break;
          }
        }
        streamlines.pop_back();
      }
    }
  }

  return status;
}
