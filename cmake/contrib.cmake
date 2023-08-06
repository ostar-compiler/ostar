iostar_file_glob(GLOB CSOURCE_RELAY_CONTRIB_SRC src/relay/backend/contrib/codegen_c/*.cc)
list(APPEND COMPILER_SRCS ${CSOURCE_RELAY_CONTRIB_SRC})

ostar_file_glob(GLOB EXAMPLE_TARGET_HOOKS_SRC src/relay/backend/contrib/example_target_hooks/*.cc)
list(APPEND COMPILER_SRCS ${EXAMPLE_TARGET_HOOKS_SRC})

message(STATUS "Build with contrib.hybriddump")
ostar_file_glob(GLOB HYBRID_CONTRIB_SRC src/contrib/hybrid/*.cc)
list(APPEND COMPILER_SRCS ${HYBRID_CONTRIB_SRC})

if(USE_LIBTORCH)
  find_package(Torch REQUIRED PATHS ${USE_LIBTORCH}/share/cmake/Torch
               )
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${TORCH_LIBRARIES})
  include_directories(${TORCH_INCLUDE_DIRS})

  file(GLOB LIBTORCH_RELAY_CONTRIB_SRC
    src/relay/backend/contrib/libtorch/libtorch_codegen.cc
    src/runtime/contrib/libtorch/libtorch_runtime.cc
    )
  list(APPEND COMPILER_SRCS ${LIBTORCH_RELAY_CONTRIB_SRC})

endif(USE_LIBTORCH)

if(USE_NNPACK)
  if(NNPACK_PATH STREQUAL "")
    set(NNPACK_PATH ${CMAKE_CURRENT_SOURCE_DIR}/NNPack)
  endif()
	set(PTHREAD_POOL_PATH ${NNPACK_PATH}/deps/pthreadpool)
  ostar_file_glob(GLOB NNPACK_CONTRIB_SRC src/runtime/contrib/nnpack/*.cc)
  list(APPEND RUNTIME_SRCS ${NNPACK_CONTRIB_SRC})
	include_directories(${NNPACK_PATH}/include)
	include_directories(${PTHREAD_POOL_PATH}/include)
  find_library(NNPACK_CONTRIB_LIB nnpack ${NNPACK_PATH}/lib)
  find_library(NNPACK_PTHREAD_CONTRIB_LIB pthreadpool ${NNPACK_PATH}/lib)
  find_library(NNPACK_CPUINFO_CONTRIB_LIB cpuinfo ${NNPACK_PATH}/lib)
  find_library(NNPACK_CLOG_CONTRIB_LIB clog ${NNPACK_PATH}/lib)

  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${NNPACK_CONTRIB_LIB})
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${NNPACK_PTHREAD_CONTRIB_LIB})
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${NNPACK_CPUINFO_CONTRIB_LIB})
  list(APPEND OSTAR_RUNTIME_LINKER_LIBS ${NNPACK_CLOG_CONTRIB_LIB})
endif(USE_NNPACK)

if(USE_TARGET_ONNX)
  message(STATUS "Build with contrib.codegen_onnx")
  ostar_file_glob(GLOB ONNX_CONTRIB_SRC src/runtime/contrib/onnx/onnx_module.cc)
  list(APPEND RUNTIME_SRCS ${ONNX_CONTRIB_SRC})
endif(USE_TARGET_ONNX)

if(USE_PAPI)
  find_package(PkgConfig REQUIRED)

  set(ENV{PKG_CONFIG_PATH} "${USE_PAPI}:$ENV{PKG_CONFIG_PATH}")
  pkg_check_modules(PAPI REQUIRED IMPORTED_TARGET papi>=6.0)
  message(STATUS "Using PAPI library ${PAPI_LINK_LIBRARIES}")
  target_link_libraries(ostar_runtime_objs PRIVATE PkgConfig::PAPI)
  target_link_libraries(ostar PRIVATE PkgConfig::PAPI)
  target_link_libraries(ostar PRIVATE PkgConfig::PAPI)
  target_sources(ostar_runtime_objs PRIVATE src/runtime/contrib/papi/papi.cc)
endif()

if(USE_RANDOM)
  message(STATUS "Build with contrib.random")
  ostar_file_glob(GLOB RANDOM_CONTRIB_SRC src/runtime/contrib/random/random.cc)
  list(APPEND RUNTIME_SRCS ${RANDOM_CONTRIB_SRC})
endif(USE_RANDOM)

if(USE_SORT)
  message(STATUS "Build with contrib.sort")
  ostar_file_glob(GLOB SORT_CONTRIB_SRC src/runtime/contrib/sort/*.cc)
  list(APPEND RUNTIME_SRCS ${SORT_CONTRIB_SRC})
endif(USE_SORT)

