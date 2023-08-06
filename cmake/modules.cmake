# clang falgs
if ("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang")
  EXECUTE_PROCESS(COMMAND ${CMAKE_CXX_COMPILER} --version OUTPUT_VARIABLE clang_full_version)
  string (REGEX REPLACE ".*clang version ([0-9]+\\.[0-9]+).*" "\\1" CLANG_VERSION ${clang_full_version})
  message(STATUS "CLANG_VERSION ${CLANG_VERSION}")
  # cmake 3.2 does not support VERSION_GREATER_EQUAL
  set(CLANG_MINIMUM_VERSION 10.0)
  if ((CLANG_VERSION VERSION_GREATER ${CLANG_MINIMUM_VERSION})
      OR
      (CLANG_VERSION VERSION_GREATER ${CLANG_MINIMUM_VERSION}))
    message(STATUS "Setting enhanced clang warning flags")

    set(warning_opts
      -Wno-c++98-compat
      -Wno-c++98-compat-extra-semi
      -Wno-c++98-compat-pedantic
      -Wno-padded
      -Wno-extra-semi
      -Wno-extra-semi-stmt
      -Wno-unused-parameter
      -Wno-sign-conversion
      -Wno-weak-vtables
      -Wno-deprecated-copy-dtor
      -Wno-global-constructors
      -Wno-double-promotion
      -Wno-float-equal
      -Wno-missing-prototypes
      -Wno-implicit-int-float-conversion
      -Wno-implicit-float-conversion
      -Wno-implicit-int-conversion
      -Wno-float-conversion
      -Wno-shorten-64-to-32
      -Wno-covered-switch-default
      -Wno-unused-exception-parameter
      -Wno-return-std-move
      -Wno-over-aligned
      -Wno-undef
      -Wno-inconsistent-missing-destructor-override
      -Wno-unreachable-code
      -Wno-deprecated-copy
      -Wno-implicit-fallthrough
      -Wno-unreachable-code-return
      -Wno-non-virtual-dtor
      -Wreserved-id-macro
      -Wused-but-marked-unused
      -Wdocumentation-unknown-command
      -Wcast-qual
      -Wzero-as-null-pointer-constant
      -Wno-documentation
      -Wno-shadow-uncaptured-local
      -Wno-shadow-field-in-constructor
      -Wno-shadow
      -Wno-shadow-field
      -Wno-exit-time-destructors
      -Wno-switch-enum
      -Wno-old-style-cast
      -Wno-gnu-anonymous-struct
      -Wno-nested-anon-types
    )
  target_compile_options(ostar_objs PRIVATE $<$<COMPILE_LANGUAGE:CXX>: ${warning_opts}>)
  target_compile_options(ostar_runtime_objs PRIVATE $<$<COMPILE_LANGUAGE:CXX>: ${warning_opts}>)


  endif ()
endif ("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang")

# cuda dependons
# CUDA Module
find_cuda(${USE_CUDA} ${USE_CUDNN})

if(CUDA_FOUND)
  include_directories(SYSTEM ${CUDA_INCLUDE_DIRS})
endif(CUDA_FOUND)

if(USE_CUDA)
  if(NOT CUDA_FOUND)
    message(FATAL_ERROR "Cannot find CUDA, USE_CUDA=" ${USE_CUDA})
  endif()
  message(STATUS "Build with CUDA ${CUDA_VERSION} support")
  ostar_file_glob(GLOB RUNTIME_CUDA_SRCS src/runtime/cuda/*.cc)
  list(APPEND RUNTIME_SRCS ${RUNTIME_CUDA_SRCS})
  list(APPEND COMPILER_SRCS src/target/opt/build_cuda_on.cc)

  list(APPEND OSTAR_LINKER_LIBS ${CUDA_NVRTC_LIBRARY})
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${CUDA_CUDART_LIBRARY})
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${CUDA_CUDA_LIBRARY})
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${CUDA_NVRTC_LIBRARY})

  if(USE_CUDNN)
    message(STATUS "Build with cuDNN support")
    include_directories(SYSTEM ${CUDA_CUDNN_INCLUDE_DIRS})
    ostar_file_glob(GLOB CUDNN_RELAY_CONTRIB_SRC src/relay/backend/contrib/cudnn/*.cc)
    list(APPEND COMPILER_SRCS ${CUDNN_RELAY_CONTRIB_SRC})
    ostar_file_glob(GLOB CONTRIB_CUDNN_SRCS src/runtime/contrib/cudnn/*.cc)
    list(APPEND RUNTIME_SRCS ${CONTRIB_CUDNN_SRCS})
    list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${CUDA_CUDNN_LIBRARY})
  endif(USE_CUDNN)

  if(USE_THRUST)
    message(STATUS "Build with Thrust support")
    cmake_minimum_required(VERSION 3.13) # to compile CUDA code
    enable_language(CUDA)
    set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} --expt-extended-lambda")
    ostar_file_glob(GLOB CONTRIB_THRUST_SRC src/runtime/contrib/thrust/*.cu)
    list(APPEND RUNTIME_SRCS ${CONTRIB_THRUST_SRC})
  endif(USE_THRUST)

  if(USE_CURAND)
    message(STATUS "Build with cuRAND support")
    message(STATUS "${CUDA_CURAND_LIBRARY}")
    cmake_minimum_required(VERSION 3.13)
    enable_language(CUDA)
    ostar_file_glob(GLOB CONTRIB_CURAND_SRC_CC src/runtime/contrib/curand/*.cc)
    ostar_file_glob(GLOB CONTRIB_CURAND_SRC_CU src/runtime/contrib/curand/*.cu)
    list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${CUDA_CURAND_LIBRARY})
    list(APPEND RUNTIME_SRCS ${CONTRIB_CURAND_SRC_CC})
    list(APPEND RUNTIME_SRCS ${CONTRIB_CURAND_SRC_CU})
  endif(USE_CURAND)

  if(USE_GRAPH_EXECUTOR_CUDA_GRAPH)
    if(NOT USE_GRAPH_EXECUTOR)
      message(FATAL_ERROR "CUDA Graph is only supported by graph executor, please set USE_GRAPH_EXECUTOR=ON")
    endif()
    if(CUDAToolkit_VERSION_MAJOR LESS "10")
      message(FATAL_ERROR "CUDA Graph requires CUDA 10 or above, got=" ${CUDAToolkit_VERSION})
    endif()
    message(STATUS "Build with Graph executor with CUDA Graph support...")
    ostar_file_glob(GLOB RUNTIME_CUDA_GRAPH_SRCS src/runtime/graph_executor/cuda_graph/*.cc)
    list(APPEND RUNTIME_SRCS ${RUNTIME_CUDA_GRAPH_SRCS})
  endif()
else(USE_CUDA)
  list(APPEND COMPILER_SRCS src/target/opt/build_cuda_off.cc)
endif(USE_CUDA)

# git dependons

find_package(Git QUIET)
if (${GIT_FOUND})
  message(STATUS "Git found: ${GIT_EXECUTABLE}")
  execute_process(COMMAND ${GIT_EXECUTABLE} rev-parse HEAD
                  WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
                  OUTPUT_VARIABLE OSTAR_GIT_COMMIT_HASH
                  RESULT_VARIABLE _OSTAR_GIT_RESULT
                  ERROR_VARIABLE _OSTAR_GIT_ERROR
                  OUTPUT_STRIP_TRAILING_WHITESPACE
                  ERROR_STRIP_TRAILING_WHITESPACE)
  if (${_OSTAR_GIT_RESULT} EQUAL 0)
    message(STATUS "Found OSTAR_GIT_COMMIT_HASH=${OSTAR_GIT_COMMIT_HASH}")
  else()
    message(STATUS "Not a git repo")
    set(OSTAR_GIT_COMMIT_HASH "NOT-FOUND")
  endif()

  execute_process(COMMAND ${GIT_EXECUTABLE} show -s --format=%ci HEAD
                  WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
                  OUTPUT_VARIABLE OSTAR_GIT_COMMIT_TIME
                  RESULT_VARIABLE _OSTAR_GIT_RESULT
                  ERROR_VARIABLE _OSTAR_GIT_ERROR
                  OUTPUT_STRIP_TRAILING_WHITESPACE
                  ERROR_STRIP_TRAILING_WHITESPACE)
  if (${_OSTAR_GIT_RESULT} EQUAL 0)
    message(STATUS "Found OSTAR_GIT_COMMIT_TIME=${OSTAR_GIT_COMMIT_TIME}")
  else()
    set(OSTAR_GIT_COMMIT_TIME "NOT-FOUND")
  endif()
else()
  message(WARNING "Git not found")
  set(OSTAR_GIT_COMMIT_HASH "NOT-FOUND")
  set(OSTAR_GIT_COMMIT_TIME "NOT-FOUND")
endif()

# libinfo dependons
function(add_lib_info src_file)
  if (NOT DEFINED OSTAR_INFO_LLVM_VERSION)
    set(OSTAR_INFO_LLVM_VERSION "NOT-FOUND")
  else()
    string(STRIP ${OSTAR_INFO_LLVM_VERSION} OSTAR_INFO_LLVM_VERSION)
  endif()
  if (NOT DEFINED CUDA_VERSION)
    set(OSTAR_INFO_CUDA_VERSION "NOT-FOUND")
  else()
    string(STRIP ${CUDA_VERSION} OSTAR_INFO_CUDA_VERSION)
  endif()

  set_property(
    SOURCE ${src_file}
    APPEND
    PROPERTY COMPILE_DEFINITIONS
    OSTAR_CXX_COMPILER_PATH="${CMAKE_CXX_COMPILER}"
    OSTAR_INFO_BUILD_STATIC_RUNTIME="${BUILD_STATIC_RUNTIME}"
    OSTAR_INFO_COMPILER_RT_PATH="${COMPILER_RT_PATH}"
    OSTAR_INFO_CUDA_VERSION="${OSTAR_INFO_CUDA_VERSION}"
    OSTAR_INFO_DLPACK_PATH="${DLPACK_PATH}"
    OSTAR_INFO_DMLC_PATH="${DMLC_PATH}"
    OSTAR_INFO_GIT_COMMIT_HASH="${OSTAR_GIT_COMMIT_HASH}"
    OSTAR_INFO_GIT_COMMIT_TIME="${OSTAR_GIT_COMMIT_TIME}"
    OSTAR_INFO_HIDE_PRIVATE_SYMBOLS="${HIDE_PRIVATE_SYMBOLS}"
    OSTAR_INFO_INDEX_DEFAULT_I64="${INDEX_DEFAULT_I64}"
    OSTAR_INFO_INSTALL_DEV="${INSTALL_DEV}"
    OSTAR_INFO_LLVM_VERSION="${OSTAR_INFO_LLVM_VERSION}"
    OSTAR_INFO_PICOJSON_PATH="${PICOJSON_PATH}"
    OSTAR_INFO_RANG_PATH="${RANG_PATH}"
    OSTAR_INFO_ROCM_PATH="${ROCM_PATH}"
    OSTAR_INFO_SUMMARIZE="${SUMMARIZE}"
    OSTAR_INFO_USE_ALTERNATIVE_LINKER="${USE_ALTERNATIVE_LINKER}"
    OSTAR_INFO_USE_AOT_EXECUTOR="${USE_AOT_EXECUTOR}"
    OSTAR_INFO_USE_CMSISNN="${USE_CMSISNN}"
    OSTAR_INFO_USE_CPP_RPC="${USE_CPP_RPC}"
    OSTAR_INFO_USE_CPP_ROSTAR="${USE_CPP_ROSTAR}"
    OSTAR_INFO_USE_CUDA="${USE_CUDA}"
    OSTAR_INFO_USE_CUDNN="${USE_CUDNN}"
    OSTAR_INFO_USE_CUSTOM_LOGGING="${USE_CUSTOM_LOGGING}"
    OSTAR_INFO_USE_FALLBACK_STL_MAP="${USE_FALLBACK_STL_MAP}"
    OSTAR_INFO_USE_GRAPH_EXECUTOR_CUDA_GRAPH="${USE_GRAPH_EXECUTOR_CUDA_GRAPH}"
    OSTAR_INFO_USE_GRAPH_EXECUTOR="${USE_GRAPH_EXECUTOR}"
    OSTAR_INFO_USE_GTEST="${USE_GTEST}"
    OSTAR_INFO_USE_IOS_RPC="${USE_IOS_RPC}"
    OSTAR_INFO_USE_KHRONOS_SPIRV="${USE_KHRONOS_SPIRV}"
    OSTAR_INFO_USE_LIBBACKTRACE="${USE_LIBBACKTRACE}"
    OSTAR_INFO_USE_LIBTORCH="${USE_LIBTORCH}"
    OSTAR_INFO_USE_LLVM="${USE_LLVM}"
    OSTAR_INFO_USE_MKL="${USE_MKL}"
    OSTAR_INFO_USE_OPENMP="${USE_OPENMP}"
    OSTAR_INFO_USE_PAPI="${USE_PAPI}"
    OSTAR_INFO_USE_PROFILER="${USE_PROFILER}"
    OSTAR_INFO_USE_RANDOM="${USE_RANDOM}"
    OSTAR_INFO_USE_RPC="${USE_RPC}"
    OSTAR_INFO_USE_SORT="${USE_SORT}"
    OSTAR_INFO_USE_STACKVM_RUNTIME="${USE_STACKVM_RUNTIME}"
    OSTAR_INFO_USE_TARGET_ONNX="${USE_TARGET_ONNX}"
    OSTAR_INFO_USE_THREADS="${USE_THREADS}"
    OSTAR_INFO_USE_THRUST="${USE_THRUST}"
    OSTAR_INFO_USE_CURAND="${USE_CURAND}"
    OSTAR_INFO_USE_CCACHE="${USE_CCACHE}"
    OSTAR_INFO_BACKTRACE_ON_SEGFAULT="${BACKTRACE_ON_SEGFAULT}"
  )

endfunction()

# llvm dependons
add_definitions(-DDMLC_USE_FOPEN64=0 -DNDEBUG=1)

if(NOT ${USE_LLVM} MATCHES ${IS_FALSE_PATTERN})
  find_llvm(${USE_LLVM})
  include_directories(SYSTEM ${LLVM_INCLUDE_DIRS})
  add_definitions(${LLVM_DEFINITIONS})
  message(STATUS "Build with LLVM " ${LLVM_PACKAGE_VERSION})
  message(STATUS "Set OSTAR_LLVM_VERSION=" ${OSTAR_LLVM_VERSION})

  add_definitions(-DOSTAR_LLVM_VERSION=${OSTAR_LLVM_VERSION})
  ostar_file_glob(GLOB COMPILER_LLVM_SRCS src/target/llvm/*.cc)
  list(APPEND OSTAR_LINKER_LIBS ${LLVM_LIBS})
  list(APPEND COMPILER_SRCS ${COMPILER_LLVM_SRCS})
  if(NOT MSVC)
    set_source_files_properties(${COMPILER_LLVM_SRCS}
      PROPERTIES COMPILE_DEFINITIONS "DMLC_ENABLE_RTTI=0")
    set_source_files_properties(${COMPILER_LLVM_SRCS}
      PROPERTIES COMPILE_FLAGS "-fno-rtti")
  endif()
endif()

# logging dependons
include(FindPackageHandleStandardArgs)

if(USE_CUSTOM_LOGGING)
  # Set and propogate OSTAR_LOG_CUSTOMIZE flag is custom logging has been requested
  target_compile_definitions(ostar_objs PUBLIC OSTAR_LOG_CUSTOMIZE=1)
  target_compile_definitions(ostar_runtime_objs PUBLIC OSTAR_LOG_CUSTOMIZE=1)
  target_compile_definitions(ostar_libinfo_objs PUBLIC OSTAR_LOG_CUSTOMIZE=1)
  target_compile_definitions(ostar PUBLIC OSTAR_LOG_CUSTOMIZE=1)
  target_compile_definitions(ostar_runtime PUBLIC OSTAR_LOG_CUSTOMIZE=1)
endif()

add_library(libbacktrace STATIC IMPORTED)

set(LIBBACKTRACE_INCLUDE_DIR NOTFOUND)
set(LIBBACKTRACE_STATIC_LIBRARY NOTFOUND)
set(LIBBACKTRACE_FOUND NO)

macro(__find_libbacktrace)
  find_path(LIBBACKTRACE_INCLUDE_DIR backtrace.h)
  find_library(LIBBACKTRACE_STATIC_LIBRARY libbacktrace.a)
  find_package_handle_standard_args(LIBBACKTRACE REQUIRED_VARS
    LIBBACKTRACE_STATIC_LIBRARY LIBBACKTRACE_INCLUDE_DIR)
endmacro()

macro(__find_libbacktrace_from PATH)
  find_path(LIBBACKTRACE_INCLUDE_DIR backtrace.h
    PATHS ${PATH}
    PATH_SUFFIXES include
    NO_CMAKE_SYSTEM_PATH
    NO_SYSTEM_ENVIRONMENT_PATH
  )
  find_library(LIBBACKTRACE_STATIC_LIBRARY libbacktrace.a
    PATHS ${PATH}
    PATH_SUFFIXES lib
    NO_CMAKE_SYSTEM_PATH
    NO_SYSTEM_ENVIRONMENT_PATH
  )
  find_package_handle_standard_args(LIBBACKTRACE REQUIRED_VARS
    LIBBACKTRACE_STATIC_LIBRARY LIBBACKTRACE_INCLUDE_DIR)
endmacro()

macro(__compile_libbacktrace)
  message(STATUS "Building libbacktrace from 3rdparty/libbacktrace")
  include(cmake/libs/Libbacktrace.cmake)
  add_dependencies(libbacktrace project_libbacktrace)
  set(LIBBACKTRACE_INCLUDE_DIR ${CMAKE_CURRENT_BINARY_DIR}/libbacktrace/include)
  set(LIBBACKTRACE_STATIC_LIBRARY ${CMAKE_CURRENT_BINARY_DIR}/libbacktrace/lib/libbacktrace.a)
  add_dependencies(ostar_runtime_objs libbacktrace)
  set(LIBBACKTRACE_FOUND YES)
endmacro()

if(USE_LIBBACKTRACE STREQUAL "AUTO")
  __find_libbacktrace()
  if(NOT LIBBACKTRACE_FOUND AND (CMAKE_SYSTEM_NAME MATCHES "Linux" OR CMAKE_SYSTEM_NAME MATCHES "Darwin"))
    __compile_libbacktrace()
  endif()
elseif(USE_LIBBACKTRACE STREQUAL "COMPILE")
  __compile_libbacktrace()
elseif("${USE_LIBBACKTRACE}" MATCHES ${IS_TRUE_PATTERN})
  __find_libbacktrace()
  if(NOT LIBBACKTRACE_FOUND)
    message(SEND_ERROR "libbacktrace not found. (Set USE_LIBBACKTRACE to COMPILE if you want to build with the submodule at 3rdparty/libbacktrace.)")
  endif()
elseif("${USE_LIBBACKTRACE}" MATCHES ${IS_FALSE_PATTERN})
else()
  # Treat USE_LIBBACKTRACE as path to libbacktrace
  message(STATUS "Using libbacktrace from ${USE_LIBBACKTRACE}")
  __find_libbacktrace_from(${USE_LIBBACKTRACE})
  if(NOT LIBBACKTRACE_FOUND)
    message(SEND_ERROR "libbacktrace not found from ${USE_LIBBACKTRACE}.")
  endif()
endif()

set_property(TARGET libbacktrace
  PROPERTY IMPORTED_LOCATION ${LIBBACKTRACE_STATIC_LIBRARY})

function(configure_backtrace TARGET)
  if(LIBBACKTRACE_FOUND)
    get_target_property(target_type ${TARGET} TYPE)
    if(target_type MATCHES "EXECUTABLE|(STATIC|SHARED|MODULE)_LIBRARY")
      target_link_libraries(${TARGET} PRIVATE libbacktrace)
    endif()
    target_include_directories(${TARGET} PRIVATE ${LIBBACKTRACE_INCLUDE_DIR})
    target_compile_definitions(${TARGET} PRIVATE OSTAR_USE_LIBBACKTRACE=1)
  else()
    target_compile_definitions(${TARGET} PRIVATE OSTAR_USE_LIBBACKTRACE=0)
  endif()

  if(BACKTRACE_ON_SEGFAULT)
    target_compile_definitions(${TARGET} PRIVATE OSTAR_BACKTRACE_ON_SEGFAULT)
  endif()
endfunction()

configure_backtrace(ostar)
configure_backtrace(ostar_runtime)
configure_backtrace(ostar_objs)
configure_backtrace(ostar_runtime_objs)

# openmp dependons 
if(USE_OPENMP STREQUAL "gnu")
  find_package(OpenMP)
  if(OPENMP_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${OpenMP_CXX_LIBRARIES})
    add_definitions(-DOSTAR_THREADPOOL_USE_OPENMP=1)
    message(STATUS "Build with OpenMP ${OpenMP_CXX_LIBRARIES}")
  else()
    add_definitions(-DOSTAR_THREADPOOL_USE_OPENMP=0)
    message(WARNING "OpenMP cannot be found, use OSTAR threadpool instead.")
  endif()
elseif(USE_OPENMP STREQUAL "intel")
  find_package(OpenMP)
  if(OPENMP_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    if (MSVC)
      find_library(OMP_LIBRARY NAMES libiomp5md)
    else()
      find_library(OMP_LIBRARY NAMES iomp5)
    endif()
    list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${OMP_LIBRARY})
    add_definitions(-DOSTAR_THREADPOOL_USE_OPENMP=1)
    message(STATUS "Build with OpenMP " ${OMP_LIBRARY})
  else()
    add_definitions(-DOSTAR_THREADPOOL_USE_OPENMP=0)
    message(WARNING "OpenMP cannot be found, use OSTAR threadpool instead.")
  endif()
else()
  add_definitions(-DOSTAR_THREADPOOL_USE_OPENMP=0)
endif()

# vta dependons 
find_program(PYTHON NAMES python python3 python3.6)

# Throw error if VTA_HW_PATH is not set
if(NOT DEFINED ENV{VTA_HW_PATH})
  set(VTA_HW_PATH ${CMAKE_CURRENT_SOURCE_DIR}/3rdparty/vta-hw)
else()
  set(VTA_HW_PATH $ENV{VTA_HW_PATH})
endif()

if(MSVC)
  message(STATUS "VTA build is skipped in Windows..")
elseif(NOT EXISTS ${VTA_HW_PATH})
  if (USE_VTA_TSIM OR USE_VTA_FSIM OR USE_UFPGA)
    message(FATAL_ERROR "VTA path " ${VTA_HW_PATH} " does not exist")
  endif()
elseif(PYTHON)
  message(STATUS "VTA build with VTA_HW_PATH=" ${VTA_HW_PATH})
  set(VTA_CONFIG ${PYTHON} ${VTA_HW_PATH}/config/vta_config.py)

  if(EXISTS ${CMAKE_CURRENT_BINARY_DIR}/vta_config.json)
    message(STATUS "Use VTA config " ${CMAKE_CURRENT_BINARY_DIR}/vta_config.json)
    set(VTA_CONFIG ${PYTHON} ${VTA_HW_PATH}/config/vta_config.py
      --use-cfg=${CMAKE_CURRENT_BINARY_DIR}/vta_config.json)
  endif()

  execute_process(COMMAND ${VTA_CONFIG} --target OUTPUT_VARIABLE VTA_TARGET OUTPUT_STRIP_TRAILING_WHITESPACE)

  message(STATUS "Build VTA runtime with target: " ${VTA_TARGET})

  execute_process(COMMAND ${VTA_CONFIG} --defs OUTPUT_VARIABLE __vta_defs)

  string(REGEX MATCHALL "(^| )-D[A-Za-z0-9_=.]*" VTA_DEFINITIONS "${__vta_defs}")

  # Fast simulator driver build
  if(USE_VTA_FSIM)
    # Add fsim driver sources
    ostar_file_glob(GLOB FSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/*.cc)
    ostar_file_glob(GLOB FSIM_RUNTIME_SRCS vta/runtime/*.cc)
    list(APPEND FSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/sim/sim_driver.cc)
    list(APPEND FSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/sim/sim_tlpp.cc)
    list(APPEND FSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/vmem/virtual_memory.cc)
    # Target lib: vta_fsim
    add_library(vta_fsim SHARED ${FSIM_RUNTIME_SRCS})
    target_include_directories(vta_fsim SYSTEM PUBLIC ${VTA_HW_PATH}/include)
    target_compile_definitions(vta_fsim PUBLIC DMLC_USE_LOGGING_LIBRARY=<ostar/runtime/logging.h>)
    foreach(__def ${VTA_DEFINITIONS})
      string(SUBSTRING ${__def} 3 -1 __strip_def)
      target_compile_definitions(vta_fsim PUBLIC ${__strip_def})
    endforeach()
    if(APPLE)
      set_property(TARGET vta_fsim APPEND PROPERTY LINK_FLAGS "-undefined dynamic_lookup")
    endif(APPLE)
    target_compile_definitions(vta_fsim PUBLIC USE_FSIM_TLPP)
  endif()

  # Cycle accurate simulator driver build
  if(USE_VTA_TSIM)
    if(DEFINED ENV{VERILATOR_INC_DIR})
      set(VERILATOR_INC_DIR $ENV{VERILATOR_INC_DIR})
    elseif (EXISTS /usr/local/share/verilator/include)
      set(VERILATOR_INC_DIR /usr/local/share/verilator/include)
    elseif (EXISTS /usr/share/verilator/include)
      set(VERILATOR_INC_DIR /usr/share/verilator/include)
    else()
      message(STATUS "Verilator not found in /usr/local/share/verilator/include")
      message(STATUS "Verilator not found in /usr/share/verilator/include")
      message(FATAL_ERROR "Cannot find Verilator, VERILATOR_INC_DIR is not defined")
    endif()
    # Add tsim driver sources
    ostar_file_glob(GLOB TSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/*.cc)
    ostar_file_glob(GLOB TSIM_RUNTIME_SRCS vta/runtime/*.cc)
    list(APPEND TSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/tsim/tsim_driver.cc)
    list(APPEND TSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/dpi/module.cc)
    list(APPEND TSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/vmem/virtual_memory.cc)
    # Target lib: vta_tsim
    add_library(vta_tsim SHARED ${TSIM_RUNTIME_SRCS})
    target_include_directories(vta_tsim SYSTEM PUBLIC ${VTA_HW_PATH}/include ${VERILATOR_INC_DIR} ${VERILATOR_INC_DIR}/vltstd)
    target_compile_definitions(vta_tsim PUBLIC DMLC_USE_LOGGING_LIBRARY=<ostar/runtime/logging.h>)
    foreach(__def ${VTA_DEFINITIONS})
      string(SUBSTRING ${__def} 3 -1 __strip_def)
      target_compile_definitions(vta_tsim PUBLIC ${__strip_def})
    endforeach()
    if(APPLE)
      set_property(TARGET vta_fsim APPEND PROPERTY LINK_FLAGS "-undefined dynamic_lookup")
    endif(APPLE)
  endif()

  # VTA FPGA driver sources
  if(USE_VTA_FPGA)
    ostar_file_glob(GLOB FSIM_RUNTIME_SRCS ${VTA_HW_PATH}/src/*.cc)
    ostar_file_glob(GLOB FPGA_RUNTIME_SRCS vta/runtime/*.cc)
    # Rules for Zynq-class FPGAs with pynq OS support (see pynq.io)
    if(${VTA_TARGET} STREQUAL "pynq" OR
       ${VTA_TARGET} STREQUAL "ultra96")
      list(APPEND FPGA_RUNTIME_SRCS ${VTA_HW_PATH}/src/pynq/pynq_driver.cc)
      # Rules for Pynq v2.4
      find_library(__cma_lib NAMES cma PATH /usr/lib)
    elseif(${VTA_TARGET} STREQUAL "de10nano")  # DE10-Nano rules
      ostar_file_glob(GLOB DE10_FPGA_RUNTIME_SRCS ${VTA_HW_PATH}/src/de10nano/*.cc ${VTA_HW_PATH}/src/*.cc)
      list(APPEND FPGA_RUNTIME_SRCS ${DE10_FPGA_RUNTIME_SRCS})
    elseif(${VTA_TARGET} STREQUAL "intelfocl")  # Intel OpenCL for FPGA rules
      ostar_file_glob(GLOB FOCL_SRC ${VTA_HW_PATH}/src/oclfpga/*.cc)
      list(APPEND FPGA_RUNTIME_SRCS ${FOCL_SRC})
      list(APPEND FPGA_RUNTIME_SRCS ${VTA_HW_PATH}/src/vmem/virtual_memory.cc ${VTA_HW_PATH}/src/vmem/virtual_memory.h)
    endif()
    # Target lib: vta
    add_library(vta SHARED ${FPGA_RUNTIME_SRCS})
    target_include_directories(vta PUBLIC vta/runtime)
    target_include_directories(vta PUBLIC ${VTA_HW_PATH}/include)
    target_compile_definitions(vta PUBLIC DMLC_USE_LOGGING_LIBRARY=<ostar/runtime/logging.h>)
    foreach(__def ${VTA_DEFINITIONS})
      string(SUBSTRING ${__def} 3 -1 __strip_def)
      target_compile_definitions(vta PUBLIC ${__strip_def})
    endforeach()
    if(${VTA_TARGET} STREQUAL "pynq" OR
       ${VTA_TARGET} STREQUAL "ultra96")
      target_link_libraries(vta ${__cma_lib})
    elseif(${VTA_TARGET} STREQUAL "de10nano")  # DE10-Nano rules
     #target_compile_definitions(vta PUBLIC VTA_MAX_XFER=2097152) # (1<<21)
      target_include_directories(vta SYSTEM PUBLIC ${VTA_HW_PATH}/src/de10nano)
      target_include_directories(vta SYSTEM PUBLIC 3rdparty)
      target_include_directories(vta SYSTEM PUBLIC
        "/usr/local/intelFPGA_lite/18.1/embedded/ds-5/sw/gcc/arm-linux-gnueabihf/include")
    elseif(${VTA_TARGET} STREQUAL "intelfocl")  # Intel OpenCL for FPGA rules
      target_include_directories(vta PUBLIC 3rdparty)
      set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17")
      target_link_libraries(vta -lOpenCL)
    endif()
  endif()


else()
  message(STATUS "Cannot found python in env, VTA build is skipped..")
endif()

