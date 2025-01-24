# TODO: Provide a standalone CMakeLists.txt project example
# that can link against existing amd-smi library

# copy .cc files into install directory
install(
    DIRECTORY ./
    DESTINATION ${SHARE_INSTALL_PREFIX}/example
    COMPONENT dev
    FILES_MATCHING
    PATTERN "*.cc")

# copy cmake file into install directory
install(
    FILES CMakeLists.txt.in
    RENAME CMakeLists.txt
    DESTINATION ${SHARE_INSTALL_PREFIX}/example
    COMPONENT dev)

# compile example files but do not install
# this is only useful if running from build directory
set(SMI_DRM_EXAMPLE_EXE "amd_smi_drm_ex")
add_executable(${SMI_DRM_EXAMPLE_EXE} "amd_smi_drm_example.cc")
target_link_libraries(${SMI_DRM_EXAMPLE_EXE} ${AMD_SMI_TARGET})
add_dependencies(${SMI_DRM_EXAMPLE_EXE} ${AMD_SMI_TARGET})

set(SMI_NODRM_EXAMPLE_EXE "amd_smi_nodrm_ex")
add_executable(${SMI_NODRM_EXAMPLE_EXE} "amd_smi_nodrm_example.cc")
target_link_libraries(${SMI_NODRM_EXAMPLE_EXE} ${AMD_SMI_TARGET})
add_dependencies(${SMI_NODRM_EXAMPLE_EXE} ${AMD_SMI_TARGET})

set(SMI_LIST_EXAMPLE_EXE "amd_smi_list")
add_executable(${SMI_LIST_EXAMPLE_EXE} "amd_smi_list.cc")
target_link_libraries(${SMI_LIST_EXAMPLE_EXE} ${AMD_SMI_TARGET})
add_dependencies(${SMI_LIST_EXAMPLE_EXE} ${AMD_SMI_TARGET})

if(ENABLE_ESMI_LIB)
set(ESMI_SAMPLE_EXE "amd_smi_esmi_ex")
add_executable(${ESMI_SAMPLE_EXE} "amdsmi_esmi_intg_example.cc")
target_link_libraries(${ESMI_SAMPLE_EXE} ${AMD_SMI_TARGET})
add_dependencies(${ESMI_SAMPLE_EXE} ${AMD_SMI_TARGET})
endif()
