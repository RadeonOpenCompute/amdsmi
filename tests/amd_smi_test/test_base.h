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

#ifndef TESTS_AMD_SMI_TEST_TEST_BASE_H_
#define TESTS_AMD_SMI_TEST_TEST_BASE_H_

#include <cstdint>
#include <string>
#include <vector>
#include "amd_smi/amdsmi.h"

// The max devices can be monitored
#define MAX_MONITOR_DEVICES 128
class TestBase {
 public:
  TestBase(void);

  virtual ~TestBase(void);

  enum VerboseLevel {VERBOSE_MIN = 0, VERBOSE_STANDARD, VERBOSE_PROGRESS};

  // @Brief: Before run the core measure codes, do something to set up
  // i.e. init runtime, prepare packet...
  // The init_flags option will override any flags set for the whole test
  // suite
  void SetUp(uint64_t init_flags);
  virtual void SetUp(void);

  // @Brief: Core measurement codes executing here
  virtual void Run(void);

  // @Brief: Do something clean up
  virtual void Close(void);

  // @Brief: Display the results
  virtual void DisplayResults(void) const;

  // @Brief: Display information about the test
  virtual void DisplayTestInfo(void);

  const std::string & description(void) const {return description_;}

  void set_description(std::string d);

  void set_title(std::string name) {
    title_ = name;
  }
  std::string title(void) const {
    return title_;
  }
  void set_verbosity(uint32_t v) {
    verbosity_ = v;
  }
  uint32_t verbosity(void) const {
    return verbosity_;
  }
  void set_dont_fail(bool f) {
    dont_fail_ = f;
  }
  bool dont_fail(void) const {
    return dont_fail_;
  }
  void set_num_monitor_devs(uint32_t i) {
    num_monitor_devs_ = i;
  }
  uint32_t num_monitor_devs(void) const {
    return num_monitor_devs_;
  }
  void set_init_options(uint64_t x) {
    init_options_ = x;
  }
  uint64_t init_options(void) const {
    return init_options_;
  }
  void set_num_iterations(uint32_t x) {
    num_iterations_ = x;
  }
  uint32_t num_iterations(void) const {
    return num_iterations_;
  }

 protected:
  void MakeHeaderStr(const char *inStr, std::string *outStr) const;
  void PrintDeviceHeader(amdsmi_processor_handle dv_ind);
  bool setup_failed_;   ///< Record that setup failed to return ierr in Run
  uint32_t num_monitor_devs_;  ///< Number of monitor devices found
  ///< device handles
  amdsmi_processor_handle processor_handles_[MAX_MONITOR_DEVICES];
  uint32_t socket_count_;  ///< socket count
  std::vector<amdsmi_socket_handle> sockets_;  ///< sockets

 private:
  std::string description_;
  std::string title_;   ///< Displayed title of test
  uint32_t verbosity_;   ///< How much additional output to produce
  bool dont_fail_;       ///< Don't quit test on individual failure if true
  uint64_t init_options_;  ///< rsmi initialization options
  uint32_t num_iterations_;
};

#define IF_VERB(VB) if (verbosity() && verbosity() >= (TestBase::VERBOSE_##VB))
#define IF_NVERB(VB) if (verbosity() < (TestBase::VERBOSE_##VB))

// Macros to be used within TestBase classes
#define CHK_ERR_ASRT(RET) { \
    if (dont_fail() && ((RET) != AMDSMI_STATUS_SUCCESS)) { \
        std::cout << std::endl << "\t===> TEST FAILURE." << std::endl; \
        DISPLAY_AMDSMI_ERR(RET); \
        std::cout << \
         "\t===> Abort is over-ridden due to dont_fail command line option." \
                                                               << std::endl; \
        return; \
    } \
    ASSERT_EQ(AMDSMI_STATUS_SUCCESS, (RET)); \
}

void MakeHeaderStr(const char *inStr, std::string *outStr);
extern const char kSetupLabel[];

#endif  // TESTS_AMD_SMI_TEST_TEST_BASE_H_
