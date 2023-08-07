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
    # set_source_files_properties(${COMPILER_LLVM_SRCS}
      # PROPERTIES COMPILE_FLAGS "-fno-rtti")
      # PROPERTIES COMPILE_FLAGS "-fno-rtti")
  endif()
endif()
