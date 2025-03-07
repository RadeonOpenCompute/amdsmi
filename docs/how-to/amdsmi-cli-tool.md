---
myst:
  html_meta:
    "description lang=en": "Learn how to use the AMD SMI command line tool."
    "keywords": "api, smi, lib, system, management, interface, example"
---

# AMD SMI CLI tool usage

This tool is a command line interface (CLI) for manipulating and monitoring the
`amdgpu` kernel; it is intended to replace and deprecate the existing `rocm_smi`
CLI tool and `gpuv-smi` tool. The AMD SMI CLI tool uses Ctypes to call the
`amd_smi_lib` API.

When using the CLI tool, you should have at least one AMD GPU and the driver
installed.

```{admonition} Disclaimer
The AMD SMI CLI tool is provided as an example code to aid the development of
telemetry tools. The [Python](./amdsmi-py-lib) or [C++
library](./amdsmi-cpp-lib) is recommended as a robust data source.
```

## Install the CLI Tool and Python library

Refer to the [installation instructions](../install/install.md).

## Get started

The amd-smi command provides system management and monitoring capabilities for
AMD hardware. When run without arguments, it reports the version and platform
detected:

```shell-session
~$ amd-smi
usage: amd-smi [-h]  ...

AMD System Management Interface | Version: 25.2.0 | ROCm version: 6.4.0 | Platform: Linux Baremetal

options:
  -h, --help          show this help message and exit

AMD-SMI Commands:
                      Descriptions:
    version           Display version information
    list              List GPU information
    static            Gets static information about the specified GPU
    firmware (ucode)  Gets firmware information about the specified GPU
    bad-pages         Gets bad page information about the specified GPU
    metric            Gets metric/performance information about the specified GPU
    process           Lists general process information running on the specified GPU
    event             Displays event information for the given GPU
    topology          Displays topology information of the devices
    set               Set options for devices
    reset             Reset options for devices
    monitor (dmon)    Monitor metrics for target devices
    xgmi              Displays xgmi information of the devices
```

Example commands:

```shell-session
amd-smi static --gpu 0
amd-smi metric
amd-smi process --gpu 0 1
amd-smi reset --gpureset --gpu all
```

```{note}
For command-specific help, use `amd-smi [command] --help` for see more detailed
usage information. See [Commands](#cmds).

For more detailed version information, use `amd-smi version`.
```

(cmds)=
## Commands

The following are the help output for each command, providing quick reference
details for usage.

(cmd-list)=
### amd-smi list

Lists GPU information.

```shell-session
~$ amd-smi list --help
usage: amd-smi list [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                    [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]]

Lists all the devices on the system and the links between devices.
Lists the BDF, UUID, KFD_ID, and NODE_ID for each GPU and/or CPUs.
In virtualization environments, it can also list VFs associated to each
GPU with some basic information for each VF.

options:
  -h, --help                  show this help message and exit
  -g, --gpu GPU [GPU ...]     Select a GPU ID, BDF, or UUID from the possible choices:
                              ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                all | Selects all devices
  -U, --cpu CPU [CPU ...]     Select a CPU ID from the possible choices:
                              ID: 0
                              ID: 1
                              ID: 2
                              ID: 3
                                all | Selects all devices
  -O, --core CORE [CORE ...]  Select a Core ID from the possible choices:
                              ID: 0 - 95
                                all  | Selects all devices

Command Modifiers:
  --json                      Displays output in JSON format (human readable by default).
  --csv                       Displays output in CSV format (human readable by default).
  --file FILE                 Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL            Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-static)=
### amd-smi static

Gets static information about the specified GPU. See the [sample
output](#cli-ex-static) for `amd-smi static`.

```shell-session
~$ amd-smi static --help
usage: amd-smi static [-h] [-g GPU [GPU ...] | -U CPU [CPU ...]] [-a] [-b] [-V] [-d] [-v]
                      [-c] [-B] [-R] [-r] [-p] [-l] [-P] [-x] [-u] [-s] [-i]
                      [--json | --csv] [--file FILE] [--loglevel LEVEL]

If no GPU is specified, returns static information for all GPUs on the system.
If no static argument is provided, all static information will be displayed.

Static Arguments:
  -h, --help               show this help message and exit
  -g, --gpu GPU [GPU ...]  Select a GPU ID, BDF, or UUID from the possible choices:
                           ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                           ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                           ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                           ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                             all | Selects all devices
  -U, --cpu CPU [CPU ...]  Select a CPU ID from the possible choices:
                           ID: 0
                           ID: 1
                           ID: 2
                           ID: 3
                             all | Selects all devices
  -a, --asic               All asic information
  -b, --bus                All bus information
  -V, --vbios              All video bios information (if available)
  -d, --driver             Displays driver version
  -v, --vram               All vram information
  -c, --cache              All cache information
  -B, --board              All board information
  -R, --process-isolation  The process isolation status
  -r, --ras                Displays RAS features information
  -C, --clock [CLOCK ...]  Show one or more valid clock frequency levels. Available options:
                                SYS, DF, DCEF, SOC, MEM, VCLK0, VCLK1, DCLK0, DCLK1, ALL
  -p, --partition          Partition information
  -l, --limit              All limit metric values (i.e. power and thermal limits)
  -P, --soc-pstate         The available soc pstate policy
  -x, --xgmi-plpd          The available XGMI per-link power down policy
  -u, --numa               All numa node information

CPU Arguments:
  -s, --smu                All SMU FW information
  -i, --interface-ver      Displays hsmp interface version

Command Modifiers:
  --json                   Displays output in JSON format (human readable by default).
  --csv                    Displays output in CSV format (human readable by default).
  --file FILE              Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL         Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-firmware)=
### amd-smi firmware

Gets firmware information about the specified GPU.

```shell-session
~$ amd-smi firmware --help
usage: amd-smi firmware [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                        [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]] [-f]

If no GPU is specified, return firmware information for all GPUs on the system.

Firmware Arguments:
  -h, --help                   show this help message and exit
  -g, --gpu GPU [GPU ...]      Select a GPU ID, BDF, or UUID from the possible choices:
                               ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                 all | Selects all devices
  -U, --cpu CPU [CPU ...]      Select a CPU ID from the possible choices:
                               ID: 0
                               ID: 1
                               ID: 2
                               ID: 3
                                 all | Selects all devices
  -O, --core CORE [CORE ...]   Select a Core ID from the possible choices:
                               ID: 0 - 95
                                 all  | Selects all devices
  -f, --ucode-list, --fw-list  All FW list information

Command Modifiers:
  --json                       Displays output in JSON format (human readable by default).
  --csv                        Displays output in CSV format (human readable by default).
  --file FILE                  Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL             Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-bad-pages)=
### amd-smi bad-pages

Gets bad page information about the specified GPU.

```shell-session
~$ amd-smi bad-pages --help
usage: amd-smi bad-pages [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                         [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]] [-p]
                         [-r] [-u]

If no GPU is specified, return bad page information for all GPUs on the system.

Bad Pages Arguments:
  -h, --help                  show this help message and exit
  -g, --gpu GPU [GPU ...]     Select a GPU ID, BDF, or UUID from the possible choices:
                              ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                all | Selects all devices
  -U, --cpu CPU [CPU ...]     Select a CPU ID from the possible choices:
                              ID: 0
                              ID: 1
                              ID: 2
                              ID: 3
                                all | Selects all devices
  -O, --core CORE [CORE ...]  Select a Core ID from the possible choices:
                              ID: 0 - 95
                                all  | Selects all devices
  -p, --pending               Displays all pending retired pages
  -r, --retired               Displays retired pages
  -u, --un-res                Displays unreservable pages

Command Modifiers:
  --json                      Displays output in JSON format (human readable by default).
  --csv                       Displays output in CSV format (human readable by default).
  --file FILE                 Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL            Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-metric)=
### amd-smi metric

Gets metrics and performance information about the specified GPU.

```shell-session
~$ amd-smi metric --help
usage: amd-smi metric [-h] [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]]
                      [-w INTERVAL] [-W TIME] [-i ITERATIONS] [-m] [-u] [-p] [-c] [-t]
                      [-P] [-e] [-k] [-f] [-C] [-o] [-l] [-x] [-E] [--cpu-power-metrics]
                      [--cpu-prochot] [--cpu-freq-metrics] [--cpu-c0-res]
                      [--cpu-lclk-dpm-level NBIOID] [--cpu-pwr-svi-telemetry-rails]
                      [--cpu-io-bandwidth IO_BW LINKID_NAME]
                      [--cpu-xgmi-bandwidth XGMI_BW LINKID_NAME] [--cpu-metrics-ver]
                      [--cpu-metrics-table] [--cpu-socket-energy] [--cpu-ddr-bandwidth]
                      [--cpu-temp] [--cpu-dimm-temp-range-rate DIMM_ADDR]
                      [--cpu-dimm-pow-consumption DIMM_ADDR]
                      [--cpu-dimm-thermal-sensor DIMM_ADDR] [--core-boost-limit]
                      [--core-curr-active-freq-core-limit] [--core-energy]
                      [--json | --csv] [--file FILE] [--loglevel LEVEL]

If no GPU is specified, returns metric information for all GPUs on the system.
If no metric argument is provided, all metric information will be displayed.

Metric arguments:
  -h, --help                                show this help message and exit
  -g, --gpu GPU [GPU ...]                   Select a GPU ID, BDF, or UUID from the possible choices:
                                            ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                            ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                            ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                            ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                              all | Selects all devices
  -U, --cpu CPU [CPU ...]                   Select a CPU ID from the possible choices:
                                            ID: 0
                                            ID: 1
                                            ID: 2
                                            ID: 3
                                              all | Selects all devices
  -O, --core CORE [CORE ...]                Select a Core ID from the possible choices:
                                            ID: 0 - 95
                                              all  | Selects all devices
  -w, --watch INTERVAL                      Reprint the command in a loop of INTERVAL seconds
  -W, --watch_time TIME                     The total TIME to watch the given command
  -i, --iterations ITERATIONS               Total number of ITERATIONS to loop on the given command
  -m, --mem-usage                           Memory usage per block
  -u, --usage                               Displays engine usage information
  -p, --power                               Current power usage
  -c, --clock                               Average, max, and current clock frequencies
  -t, --temperature                         Current temperatures
  -P, --pcie                                Current PCIe speed, width, and replay count
  -e, --ecc                                 Total number of ECC errors
  -k, --ecc-blocks                          Number of ECC errors per block
  -f, --fan                                 Current fan speed
  -C, --voltage-curve                       Display voltage curve
  -o, --overdrive                           Current GPU clock overdrive and GPU memory clock overdrive level
  -l, --perf-level                          Current DPM performance level
  -x, --xgmi-err                            XGMI error information since last read
  -E, --energy                              Amount of energy consumed
  -T, --throttle                            Displays throttle accumulators; Only available for MI300 or newer ASICs

CPU Arguments:
  --cpu-power-metrics                       CPU power metrics
  --cpu-prochot                             Displays prochot status
  --cpu-freq-metrics                        Displays currentFclkMemclk frequencies and cclk frequency limit
  --cpu-c0-res                              Displays C0 residency
  --cpu-lclk-dpm-level NBIOID               Displays lclk dpm level range. Requires socket ID and NBOID as inputs
  --cpu-pwr-svi-telemetry-rails             Displays svi based telemetry for all rails
  --cpu-io-bandwidth IO_BW LINKID_NAME      Displays current IO bandwidth for the selected CPU.        
                                             input parameters are bandwidth type(1) and link ID encodings        
                                             i.e. P2, P3, G0 - G7
  --cpu-xgmi-bandwidth XGMI_BW LINKID_NAME  Displays current XGMI bandwidth for the selected CPU        
                                             input parameters are bandwidth type(1,2,4) and link ID encodings        
                                             i.e. P2, P3, G0 - G7
  --cpu-metrics-ver                         Displays metrics table version
  --cpu-metrics-table                       Displays metric table
  --cpu-socket-energy                       Displays socket energy for the selected CPU socket
  --cpu-ddr-bandwidth                       Displays per socket max ddr bw, current utilized bw,        
                                             and current utilized ddr bw in percentage
  --cpu-temp                                Displays cpu socket temperature
  --cpu-dimm-temp-range-rate DIMM_ADDR      Displays dimm temperature range and refresh rate
  --cpu-dimm-pow-consumption DIMM_ADDR      Displays dimm power consumption
  --cpu-dimm-thermal-sensor DIMM_ADDR       Displays dimm thermal sensor

CPU Core Arguments:
  --core-boost-limit                        Get boost limit for the selected cores
  --core-curr-active-freq-core-limit        Get Current CCLK limit set per Core
  --core-energy                             Displays core energy for the selected core

Command Modifiers:
  --json                                    Displays output in JSON format (human readable by default).
  --csv                                     Displays output in CSV format (human readable by default).
  --file FILE                               Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL                          Set the logging level from the possible choices:
                                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-process)=
### amd-smi process

Lists general process information running on the specified GPU.

```shell-session
~$ amd-smi process --help
usage: amd-smi process [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                       [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]]
                       [-w INTERVAL] [-W TIME] [-i ITERATIONS] [-G] [-e] [-p PID]
                       [-n NAME]

If no GPU is specified, returns information for all GPUs on the system.
If no process argument is provided, all process information will be displayed.

Process arguments:
  -h, --help                   show this help message and exit
  -g, --gpu GPU [GPU ...]      Select a GPU ID, BDF, or UUID from the possible choices:
                               ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                 all | Selects all devices
  -U, --cpu CPU [CPU ...]      Select a CPU ID from the possible choices:
                               ID: 0
                               ID: 1
                               ID: 2
                               ID: 3
                                 all | Selects all devices
  -O, --core CORE [CORE ...]   Select a Core ID from the possible choices:
                               ID: 0 - 95
                                 all  | Selects all devices
  -w, --watch INTERVAL         Reprint the command in a loop of INTERVAL seconds
  -W, --watch_time TIME        The total TIME to watch the given command
  -i, --iterations ITERATIONS  Total number of ITERATIONS to loop on the given command
  -G, --general                pid, process name, memory usage
  -e, --engine                 All engine usages
  -p, --pid PID                Gets all process information about the specified process based on Process ID
  -n, --name NAME              Gets all process information about the specified process based on Process Name.                    
                               If multiple processes have the same name, information is returned for all of them.

Command Modifiers:
  --json                       Displays output in JSON format (human readable by default).
  --csv                        Displays output in CSV format (human readable by default).
  --file FILE                  Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL             Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-event)=
### amd-smi event

Displays event information for the given GPU.

```shell-session
~$ amd-smi event --help
usage: amd-smi event [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                     [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]]

If no GPU is specified, returns event information for all GPUs on the system.

Event Arguments:
  -h, --help                  show this help message and exit
  -g, --gpu GPU [GPU ...]     Select a GPU ID, BDF, or UUID from the possible choices:
                              ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                all | Selects all devices
  -U, --cpu CPU [CPU ...]     Select a CPU ID from the possible choices:
                              ID: 0
                              ID: 1
                              ID: 2
                              ID: 3
                                all | Selects all devices
  -O, --core CORE [CORE ...]  Select a Core ID from the possible choices:
                              ID: 0 - 95
                                all  | Selects all devices

Command Modifiers:
  --json                      Displays output in JSON format (human readable by default).
  --csv                       Displays output in CSV format (human readable by default).
  --file FILE                 Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL            Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-topology)=
### amd-smi topology

Displays topology information of the specified devices.

```shell-session
~$ amd-smi topology --help
usage: amd-smi topology [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                        [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]] [-a]
                        [-w] [-o] [-t] [-b]

If no GPU is specified, returns information for all GPUs on the system.
If no topology argument is provided, all topology information will be displayed.

Topology arguments:
  -h, --help                  show this help message and exit
  -g, --gpu GPU [GPU ...]     Select a GPU ID, BDF, or UUID from the possible choices:
                              ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                all | Selects all devices
  -U, --cpu CPU [CPU ...]     Select a CPU ID from the possible choices:
                              ID: 0
                              ID: 1
                              ID: 2
                              ID: 3
                                all | Selects all devices
  -O, --core CORE [CORE ...]  Select a Core ID from the possible choices:
                              ID: 0 - 95
                                all  | Selects all devices
  -a, --access                Displays link accessibility between GPUs
  -w, --weight                Displays relative weight between GPUs
  -o, --hops                  Displays the number of hops between GPUs
  -t, --link-type             Displays the link type between GPUs
  -b, --numa-bw               Display max and min bandwidth between nodes
  -c, --coherent              Display cache coherant (or non-coherant) link capability between nodes
  -n, --atomics               Display 32 and 64-bit atomic io link capability between nodes
  -d, --dma                   Display P2P direct memory access (DMA) link capability between nodes
  -z, --bi-dir                Display P2P bi-directional link capability between nodes

Command Modifiers:
  --json                      Displays output in JSON format (human readable by default).
  --csv                       Displays output in CSV format (human readable by default).
  --file FILE                 Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL            Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-set)=
### amd-smi set

Set options for specified devices.

```shell-session
~$ amd-smi set --help
usage: amd-smi set [-h] (-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]) [-f %]
                   [-l LEVEL] [-P SETPROFILE] [-d SCLKMAX] [-C PARTITION] [-M PARTITION]
                   [-o WATTS] [-p POLICY_ID] [-x POLICY_ID] [-R STATUS]
                   [--cpu-pwr-limit PWR_LIMIT] [--cpu-xgmi-link-width MIN_WIDTH MAX_WIDTH]
                   [--cpu-lclk-dpm-level NBIOID MIN_DPM MAX_DPM] [--cpu-pwr-eff-mode MODE]
                   [--cpu-gmi3-link-width MIN_LW MAX_LW] [--cpu-pcie-link-rate LINK_RATE]
                   [--cpu-df-pstate-range MAX_PSTATE MIN_PSTATE] [--cpu-enable-apb]
                   [--cpu-disable-apb DF_PSTATE] [--soc-boost-limit BOOST_LIMIT]
                   [--core-boost-limit BOOST_LIMIT] [--json | --csv] [--file FILE]
                   [--loglevel LEVEL]

If no GPU is specified, will select all GPUs on the system.
A set argument must be provided; Multiple set arguments are accepted.
Requires 'sudo' privileges.

Set Arguments:
  -h, --help                                   show this help message and exit
  -g, --gpu GPU [GPU ...]                      Select a GPU ID, BDF, or UUID from the possible choices:
                                               ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                               ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                               ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                               ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                                 all | Selects all devices
  -U, --cpu CPU [CPU ...]                                        Select a CPU ID from the possible choices:
                                                                 ID: 0
                                                                 ID: 1
                                                                 ID: 2
                                                                 ID: 3
                                                                   all | Selects all devices
  -O, --core CORE [CORE ...]                                     Select a Core ID from the possible choices:
                                                                 ID: 0 - 95
                                                                   all  | Selects all devices
  -f, --fan %                                                    Set GPU fan speed (0-255 or 0-100%)
  -l, --perf-level LEVEL                                         Set one of the following performance levels:
                                                                        AUTO, LOW, HIGH, MANUAL, STABLE_STD, STABLE_PEAK, STABLE_MIN_MCLK, STABLE_MIN_SCLK, DETERMINISM
  -P, --profile SETPROFILE                                       Set power profile level (#) or choose one of available profiles:
                                                                        CUSTOM_MASK, VIDEO_MASK, POWER_SAVING_MASK, COMPUTE_MASK, VR_MASK, THREE_D_FULL_SCR_MASK, BOOTUP_DEFAULT
  -d, --perf-determinism SCLKMAX                                 Set performance determinism and select one of the corresponding performance levels:
                                                                        AUTO, LOW, HIGH, MANUAL, STABLE_STD, STABLE_PEAK, STABLE_MIN_MCLK, STABLE_MIN_SCLK, DETERMINISM
  -C, --compute-partition <ACCELERATOR_TYPE> or <PROFILE_INDEX>  Set one of the following the accelerator type or profile index:
                                                                        SPX, TPX, CPX, 0, 1, 2.
                                                                        Use `sudo amd-smi partition --accelerator` to find acceptable values.
  -M, --memory-partition PARTITION                               Set one of the following the memory partition modes:
                                                                        NPS1, NPS2, NPS4, NPS8
  -o, --power-cap WATTS                                          Set power capacity limit:
                                                                        min cap: 0 W, max cap: 550 W
  -p, --soc-pstate POLICY_ID                                     Set the GPU soc pstate policy using policy id, an integer. Valid id's include:
                                                                        N/A
  -x, --xgmi-plpd POLICY_ID                                      Set the GPU XGMI per-link power down policy using policy id, an integer. Valid id's include:
                                                                        N/A
  -c, --clk-level CLK_TYPE [PERF_LEVELS ...]                     Set a number of sclk (aka gfxclk), mclk, fclk, pcie, or socclk frequency performance levels.
                                                                        Use `amd-smi static --clock` to find acceptable levels.
  -L, --clk-limit CLK_TYPE LIM_TYPE VALUE                        Sets the sclk (aka gfxclk) or mclk minimum and maximum frequencies. 
                                                                        ex: amd-smi set -L (sclk | mclk) (min | max) value
  -R, --process-isolation STATUS                                 Enable or disable the GPU process isolation on a per partition basis: 0 for disable and 1 for enable.

CPU Arguments:
  --cpu-pwr-limit PWR_LIMIT                                      Set power limit for the given socket. Input parameter is power limit value.
  --cpu-xgmi-link-width MIN_WIDTH MAX_WIDTH                      Set max and Min linkwidth. Input parameters are min and max link width values
  --cpu-lclk-dpm-level NBIOID MIN_DPM MAX_DPM                    Sets the max and min dpm level on a given NBIO.        
                                                                  Input parameters are die_index, min dpm, max dpm.
  --cpu-pwr-eff-mode MODE                                        Sets the power efficency mode policy. Input parameter is mode.
  --cpu-gmi3-link-width MIN_LW MAX_LW                            Sets max and min gmi3 link width range
  --cpu-pcie-link-rate LINK_RATE                                 Sets pcie link rate
  --cpu-df-pstate-range MAX_PSTATE MIN_PSTATE                    Sets max and min df-pstates
  --cpu-enable-apb                                               Enables the DF p-state performance boost algorithm
  --cpu-disable-apb DF_PSTATE                                    Disables the DF p-state performance boost algorithm. Input parameter is DFPstate (0-3)
  --soc-boost-limit BOOST_LIMIT                                  Sets the boost limit for the given socket. Input parameter is socket BOOST_LIMIT value

CPU Core Arguments:
  --core-boost-limit BOOST_LIMIT                                 Sets the boost limit for the given core. Input parameter is core BOOST_LIMIT value

Command Modifiers:
  --json                                                         Displays output in JSON format (human readable by default).
  --csv                                                          Displays output in CSV format (human readable by default).
  --file FILE                                                    Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL                                               Set the logging level from the possible choices:
                                                                        DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-reset)=
### amd-smi reset

Reset options for specified devices.

```shell-session
~$ amd-smi reset --help
usage: amd-smi reset [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                     (-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]) [-G] [-c]
                     [-f] [-p] [-x] [-d] [-C] [-M] [-o] [-l]

If no GPU is specified, will select all GPUs on the system.
A reset argument must be provided; Multiple reset arguments are accepted.
Requires 'sudo' privileges.

Reset Arguments:
  -h, --help                  show this help message and exit
  -g, --gpu GPU [GPU ...]     Select a GPU ID, BDF, or UUID from the possible choices:
                              ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                all | Selects all devices
  -U, --cpu CPU [CPU ...]     Select a CPU ID from the possible choices:
                              ID: 0
                              ID: 1
                              ID: 2
                              ID: 3
                                all | Selects all devices
  -O, --core CORE [CORE ...]  Select a Core ID from the possible choices:
                              ID: 0 - 95
                                all  | Selects all devices
  -G, --gpureset              Reset the specified GPU
  -c, --clocks                Reset clocks and overdrive to default
  -f, --fans                  Reset fans to automatic (driver) control
  -p, --profile               Reset power profile back to default
  -x, --xgmierr               Reset XGMI error counts
  -d, --perf-determinism      Disable performance determinism
  -o, --power-cap             Reset power capacity limit to max capable
  -l, --clean-local-data      Clean up local data in LDS/GPRs on a per partition basis

Command Modifiers:
  --json                      Displays output in JSON format (human readable by default).
  --csv                       Displays output in CSV format (human readable by default).
  --file FILE                 Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL            Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-monitor)=
### amd-smi monitor

Monitor metrics for target devices.

```shell-session
~$ amd-smi monitor --help
usage: amd-smi monitor [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                       [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]]
                       [-w INTERVAL] [-W TIME] [-i ITERATIONS] [-p] [-t] [-u] [-m] [-n]
                       [-d] [-e] [-v] [-r] [-q]

Monitor a target device for the specified arguments.
If no arguments are provided, all arguments will be enabled.
Use the watch arguments to run continuously.

Monitor Arguments:
  -h, --help                   show this help message and exit
  -g, --gpu GPU [GPU ...]      Select a GPU ID, BDF, or UUID from the possible choices:
                               ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                               ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                 all | Selects all devices
  -U, --cpu CPU [CPU ...]      Select a CPU ID from the possible choices:
                               ID: 0
                               ID: 1
                               ID: 2
                               ID: 3
                                 all | Selects all devices
  -O, --core CORE [CORE ...]   Select a Core ID from the possible choices:
                               ID: 0 - 95
                                 all  | Selects all devices
  -w, --watch INTERVAL         Reprint the command in a loop of INTERVAL seconds
  -W, --watch_time TIME        The total TIME to watch the given command
  -i, --iterations ITERATIONS  Total number of ITERATIONS to loop on the given command
  -p, --power-usage            Monitor power usage in Watts
  -t, --temperature            Monitor temperature in Celsius
  -u, --gfx                    Monitor graphics utilization (%) and clock (MHz)
  -m, --mem                    Monitor memory utilization (%) and clock (MHz)
  -n, --encoder                Monitor encoder utilization (%) and clock (MHz)
  -d, --decoder                Monitor decoder utilization (%) and clock (MHz)
  -e, --ecc                    Monitor ECC single bit, ECC double bit, and PCIe replay error counts
  -v, --vram-usage             Monitor memory usage in MB
  -r, --pcie                   Monitor PCIe bandwidth in Mb/s
  -q, --process                Enable Process information table below monitor output
  -V, --violation              Monitor power and thermal violation status (%); Only available for MI300 or newer ASICs

Command Modifiers:
  --json                       Displays output in JSON format (human readable by default).
  --csv                        Displays output in CSV format (human readable by default).
  --file FILE                  Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL             Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cmd-xgmi)=
### amd-smi xgmi

Displays XGMI information of specified devices.

```shell-session
~$ amd-smi xgmi --help
usage: amd-smi xgmi [-h] [--json | --csv] [--file FILE] [--loglevel LEVEL]
                    [-g GPU [GPU ...] | -U CPU [CPU ...] | -O CORE [CORE ...]] [-m]

If no GPU is specified, returns information for all GPUs on the system.
If no xgmi argument is provided, all xgmi information will be displayed.

XGMI arguments:
  -h, --help                  show this help message and exit
  -g, --gpu GPU [GPU ...]     Select a GPU ID, BDF, or UUID from the possible choices:
                              ID: 0 | BDF: 0000:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 1 | BDF: 0001:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 2 | BDF: 0002:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                              ID: 3 | BDF: 0003:01:00.0 | UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                                all | Selects all devices
  -U, --cpu CPU [CPU ...]     Select a CPU ID from the possible choices:
                              ID: 0
                              ID: 1
                              ID: 2
                              ID: 3
                                all | Selects all devices
  -O, --core CORE [CORE ...]  Select a Core ID from the possible choices:
                              ID: 0 - 95
                                all  | Selects all devices
  -m, --metric                Metric XGMI information
  -l, --link-status           XGMI Link Status information

Command Modifiers:
  --json                      Displays output in JSON format (human readable by default).
  --csv                       Displays output in CSV format (human readable by default).
  --file FILE                 Saves output into a file on the provided path (stdout by default).
  --loglevel LEVEL            Set the logging level from the possible choices:
                                DEBUG, INFO, WARNING, ERROR, CRITICAL
```

(cli-ex-static)=
### Example output from amd-smi static

To gain a sense of the AMD SMI CLI's output, the following block is sample
output from the CLI tool:

```bash
~$ amd-smi static
CPU: 0
    SMU:
        FW_VERSION: 85.90.0
    INTERFACE_VERSION:
        PROTO VERSION: 6
...

GPU: 0
    ASIC:
        MARKET_NAME: AMD Instinct MI300A
        VENDOR_ID: 0x1002
        VENDOR_NAME: Advanced Micro Devices Inc. [AMD/ATI]
        SUBVENDOR_ID: 0x1002
        DEVICE_ID: 0x74a0
        SUBSYSTEM_ID: 0x74a0
        REV_ID: 0x00
        ASIC_SERIAL: 0xXXXXXXXXXXXXXX
        OAM_ID: 0
        NUM_COMPUTE_UNITS: 228
        TARGET_GRAPHICS_VERSION: gfx942
    BUS:
        BDF: 0000:01:00.0
        MAX_PCIE_WIDTH: 16
        MAX_PCIE_SPEED: 32 GT/s
        PCIE_INTERFACE_VERSION: Gen 5
        SLOT_TYPE: PCIE
    VBIOS:
        NAME: N/A
        BUILD_DATE: N/A
        PART_NUMBER: N/A
        VERSION: N/A
    LIMIT:
        MAX_POWER: 550 W
        MIN_POWER: 0 W
        SOCKET_POWER: 550 W
        SLOWDOWN_EDGE_TEMPERATURE: N/A
        SLOWDOWN_HOTSPOT_TEMPERATURE: 100 °C
        SLOWDOWN_VRAM_TEMPERATURE: 105 °C
        SHUTDOWN_EDGE_TEMPERATURE: N/A
        SHUTDOWN_HOTSPOT_TEMPERATURE: 110 °C
        SHUTDOWN_VRAM_TEMPERATURE: 115 °C
    DRIVER:
        NAME: amdgpu
        VERSION: 6.10.10
    BOARD:
        MODEL_NUMBER: N/A
        PRODUCT_SERIAL: N/A
        FRU_ID: N/A
        PRODUCT_NAME: Aqua Vanjaram [Instinct MI300A]
        MANUFACTURER_NAME: Advanced Micro Devices, Inc. [AMD/ATI]
    RAS:
        EEPROM_VERSION: 0x21000
        PARITY_SCHEMA: DISABLED
        SINGLE_BIT_SCHEMA: DISABLED
        DOUBLE_BIT_SCHEMA: DISABLED
        POISON_SCHEMA: ENABLED
        ECC_BLOCK_STATE:
            UMC: DISABLED
            SDMA: ENABLED
            GFX: ENABLED
            MMHUB: ENABLED
            ATHUB: DISABLED
            PCIE_BIF: DISABLED
            HDP: DISABLED
            XGMI_WAFL: DISABLED
            DF: DISABLED
            SMN: DISABLED
            SEM: DISABLED
            MP0: DISABLED
            MP1: DISABLED
            FUSE: DISABLED
            MCA: DISABLED
            VCN: DISABLED
            JPEG: DISABLED
            IH: DISABLED
            MPIO: DISABLED
    PARTITION:
        COMPUTE_PARTITION: SPX
        MEMORY_PARTITION: NPS1
        PARTITION_ID: 0
    SOC_PSTATE: N/A
    XGMI_PLPD: N/A
    PROCESS_ISOLATION: Disabled
    NUMA:
        NODE: 0
        AFFINITY: 0
    VRAM:
        TYPE: HBM
        VENDOR: UNKNOWN
        SIZE: 96434 MB
        BIT_WIDTH: 8192
        MAX_BANDWIDTH: N/A 
    CACHE_INFO:
        CACHE_0:
            CACHE_PROPERTIES: DATA_CACHE, SIMD_CACHE
            CACHE_SIZE: 32 KB
            CACHE_LEVEL: 1
            MAX_NUM_CU_SHARED: 2
            NUM_CACHE_INSTANCE: 348
        CACHE_1:
            CACHE_PROPERTIES: INST_CACHE, SIMD_CACHE
            CACHE_SIZE: 64 KB
            CACHE_LEVEL: 1
            MAX_NUM_CU_SHARED: 2
            NUM_CACHE_INSTANCE: 120
        CACHE_2:
            CACHE_PROPERTIES: DATA_CACHE, SIMD_CACHE
            CACHE_SIZE: 4096 KB
            CACHE_LEVEL: 2
            MAX_NUM_CU_SHARED: 228
            NUM_CACHE_INSTANCE: 1
        CACHE_3:
            CACHE_PROPERTIES: DATA_CACHE, SIMD_CACHE
            CACHE_SIZE: 262144 KB
            CACHE_LEVEL: 3
            MAX_NUM_CU_SHARED: 228
            NUM_CACHE_INSTANCE: 1
    CLOCK:
        SYS:
            CURRENT LEVEL: 1
            FREQUENCY_LEVELS:
                LEVEL 0: 700 MHz
                LEVEL 1: 903 MHz
                LEVEL 2: 900 MHz
        MEM:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 900 MHz
                LEVEL 1: 1100 MHz
                LEVEL 2: 1200 MHz
                LEVEL 3: 1300 MHz
        DF:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 1200 MHz
                LEVEL 1: 1600 MHz
                LEVEL 2: 1900 MHz
                LEVEL 3: 2000 MHz
        SOC:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 26 MHz
                LEVEL 1: 800 MHz
                LEVEL 2: 1000 MHz
                LEVEL 3: 1143 MHz
        DCEF: N/A
        VCLK0:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 29 MHz
        VCLK1:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 29 MHz
        DCLK0:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 22 MHz
        DCLK1:
            CURRENT LEVEL: 0
            FREQUENCY_LEVELS:
                LEVEL 0: 22 MHz
...
```
