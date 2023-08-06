macro(__ostar_option variable description value)
  if(NOT DEFINED ${variable})
    set(${variable} ${value} CACHE STRING ${description})
  endif()
endmacro()

set(OSTAR_ALL_OPTIONS)

macro(ostar_option variable description value)
  set(__value ${value})
  set(__condition "")
  set(__varname "__value")
  list(APPEND OSTAR_ALL_OPTIONS ${variable})
  foreach(arg ${ARGN})
    if(arg STREQUAL "IF" OR arg STREQUAL "if")
      set(__varname "__condition")
    else()
      list(APPEND ${__varname} ${arg})
    endif()
  endforeach()
  unset(__varname)
  if("${__condition}" STREQUAL "")
    set(__condition 2 GREATER 1)
  endif()

  if(${__condition})
    if("${__value}" MATCHES ";")
      if(${__value})
        __ostar_option(${variable} "${description}" ON)
      else()
        __ostar_option(${variable} "${description}" OFF)
      endif()
    elseif(DEFINED ${__value})
      if(${__value})
        __ostar_option(${variable} "${description}" ON)
      else()
        __ostar_option(${variable} "${description}" OFF)
      endif()
    else()
      __ostar_option(${variable} "${description}" "${__value}")
    endif()
  else()
    unset(${variable} CACHE)
  endif()
endmacro()

function(assign_source_group group)
    foreach(_source IN ITEMS ${ARGN})
        if (IS_ABSOLUTE "${_source}")
            file(RELATIVE_PATH _source_rel "${CMAKE_CURRENT_SOURCE_DIR}" "${_source}")
        else()
            set(_source_rel "${_source}")
        endif()
        get_filename_component(_source_path "${_source_rel}" PATH)
        string(REPLACE "/" "\\" _source_path_msvc "${_source_path}")
        source_group("${group}\\${_source_path_msvc}" FILES "${_source}")
    endforeach()
endfunction(assign_source_group)

function(ostar_micro_add_copy_file var src dest)
    get_filename_component(basename "${src}" NAME)
    get_filename_component(dest_parent_dir "${dest}" DIRECTORY)
    add_custom_command(
        OUTPUT "${dest}"
        COMMAND "${CMAKE_COMMAND}" -E copy "${src}" "${dest}"
        DEPENDS "${src}")
    list(APPEND "${var}" "${dest}")
    set("${var}" "${${var}}" PARENT_SCOPE)
endfunction(ostar_micro_add_copy_file)

set(MICROOSTAR_TEMPLATE_PROJECTS "${CMAKE_CURRENT_BINARY_DIR}/microostar_template_projects")

set(IS_FALSE_PATTERN "^[Oo][Ff][Ff]$|^0$|^[Ff][Aa][Ll][Ss][Ee]$|^[Nn][Oo]$|^[Nn][Oo][Tt][Ff][Oo][Uu][Nn][Dd]$|.*-[Nn][Oo][Tt][Ff][Oo][Uu][Nn][Dd]$|^$")
set(IS_TRUE_PATTERN "^[Oo][Nn]$|^[1-9][0-9]*$|^[Tt][Rr][Uu][Ee]$|^[Yy][Ee][Ss]$|^[Yy]$")

if(${CMAKE_VERSION} VERSION_GREATER_EQUAL "3.12.0")
  macro(ostar_file_glob glob variable)
    file(${glob} ${variable} CONFIGURE_DEPENDS ${ARGN})
  endmacro()
else()
  macro(ostar_file_glob)
    file(${glob} ${variable} ${ARGN})
  endmacro()
endif()
function(pad_string output str padchar length)
    string(LENGTH "${str}" _strlen)
    math(EXPR _strlen "${length} - ${_strlen}")

    if(_strlen GREATER 0)
        unset(_pad)
        foreach(_i RANGE 1 ${_strlen}) # inclusive
            string(APPEND _pad ${padchar})
        endforeach()
        string(APPEND str ${_pad})
    endif()

    set(${output} "${str}" PARENT_SCOPE)
endfunction()

macro(print_summary)
    message(STATUS "  ---------------- Summary ----------------")
    message(STATUS "  CMake version         : ${CMAKE_VERSION}")
    message(STATUS "  CMake executable      : ${CMAKE_COMMAND}")
    message(STATUS "  Generator             : ${CMAKE_GENERATOR}")
    message(STATUS "  System                : ${CMAKE_SYSTEM_NAME}")
    message(STATUS "  C++ compiler          : ${CMAKE_CXX_COMPILER}")
    message(STATUS "  C++ compiler ID       : ${CMAKE_CXX_COMPILER_ID}")
    message(STATUS "  C++ compiler version  : ${CMAKE_CXX_COMPILER_VERSION}")
    message(STATUS "  CXX flags             : ${CMAKE_CXX_FLAGS}")
    message(STATUS "  CXX launcher          : ${CMAKE_CXX_COMPILER_LAUNCHER}")
    message(STATUS "  Linker flags          : ${CMAKE_SHARED_LINKER_FLAGS}")
    message(STATUS "  Build type            : ${CMAKE_BUILD_TYPE}")
    get_directory_property(READABLE_COMPILE_DEFS DIRECTORY ${PROJECT_SOURCE_DIR} COMPILE_DEFINITIONS)
    message(STATUS "  Compile definitions   : ${READABLE_COMPILE_DEFS}")

    list(SORT OSTAR_ALL_OPTIONS)
    message(STATUS "  Options:")

    # Compute padding necessary for options
    set(MAX_LENGTH 0)
    foreach(OPTION ${OSTAR_ALL_OPTIONS})
        string(LENGTH ${OPTION} OPTIONLENGTH)
        if(${OPTIONLENGTH} GREATER ${MAX_LENGTH})
            set(MAX_LENGTH ${OPTIONLENGTH})
        endif()
    endforeach()
    math(EXPR PADDING_LENGTH "${MAX_LENGTH} + 3")

    # Print each of the options (padded out so they're all aligned)
    foreach(OPTION ${OSTAR_ALL_OPTIONS})
        set(OPTION_VALUE "${${OPTION}}")
        pad_string(OUT "   ${OPTION}" " " ${PADDING_LENGTH})
        message(STATUS ${OUT} " : " ${OPTION_VALUE})
    endforeach()
endmacro()

function(dump_options_to_file ostar_options)
    file(REMOVE ${CMAKE_BINARY_DIR}/OSTARBuildOptions.txt)
    foreach(option ${ostar_options})
        file(APPEND ${CMAKE_BINARY_DIR}/OSTARBuildOptions.txt "${option} ${${option}} \n")
    endforeach()
endfunction()
function(find_and_set_linker use_alternative_linker)
  if(${use_alternative_linker} MATCHES ${IS_FALSE_PATTERN})
    return()
  endif()

  if(NOT (CMAKE_CXX_COMPILER_ID STREQUAL "Clang" OR CMAKE_CXX_COMPILER_ID STREQUAL "GNU"))
  # mold and lld only support clang and gcc
    return()
  endif()

  macro(add_to_linker_flags flag)
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${flag}" PARENT_SCOPE)
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} ${flag}" PARENT_SCOPE)
    set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} ${flag}" PARENT_SCOPE)
    message(STATUS "Added \"${flag}\" to linker flags " ${CMAKE_SHARED_LINKER_FLAGS})
  endmacro(add_to_linker_flags)

  find_program(MOLD_BIN "mold")
  find_program(LLD_BIN "lld")

  if(MOLD_BIN)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND CMAKE_CXX_COMPILER_VERSION VERSION_LESS 12.1)
      get_filename_component(MOLD_INSTALLATION_PREFIX "${MOLD_BIN}" DIRECTORY)
      get_filename_component(MOLD_INSTALLATION_PREFIX "${MOLD_INSTALLATION_PREFIX}" DIRECTORY)
      find_path(
        MOLD_LIBEXEC_DIR "ld"
        NO_DEFAULT_PATH
        HINTS "${MOLD_INSTALLATION_PREFIX}"
        PATH_SUFFIXES "libexec/mold" "lib/mold" "lib64/mold"
        NO_CACHE
      )
      if(MOLD_LIBEXEC_DIR)
        add_to_linker_flags(" -B \"${MOLD_LIBEXEC_DIR}\"")
        return()
      endif()
    else()
      add_to_linker_flags("-fuse-ld=mold")
      return()
    endif()
  elseif(LLD_BIN)
    add_to_linker_flags("-fuse-ld=lld")
  elseif(${use_alternative_linker} MATCHES ${IS_TRUE_PATTERN})
    message(FATAL_ERROR "Could not find 'mold' or 'lld' executable but USE_ALTERNATIVE_LINKER was set to ON")
  endif()

endfunction(find_and_set_linker)
macro(find_llvm use_llvm)
  if(${use_llvm} MATCHES ${IS_FALSE_PATTERN})
    return()
  endif()
  set(LLVM_CONFIG ${use_llvm})
  if(${ARGC} EQUAL 2)
    set(llvm_version_required ${ARGV1})
  endif()

  if(${LLVM_CONFIG} MATCHES ${IS_TRUE_PATTERN})
    find_package(LLVM ${llvm_version_required} REQUIRED CONFIG)
    llvm_map_components_to_libnames(LLVM_LIBS "all")
    if (NOT LLVM_LIBS)
      message(STATUS "Not found - LLVM_LIBS")
      message(STATUS "Fall back to using llvm-config")
      set(LLVM_CONFIG "${LLVM_TOOLS_BINARY_DIR}/llvm-config")
    endif()
  endif()

  if(LLVM_LIBS) # check if defined, not if it is true
    list (FIND LLVM_LIBS "LLVM" _llvm_dynlib_index)
    if (${_llvm_dynlib_index} GREATER -1)
      set(LLVM_LIBS LLVM)
      message(STATUS "Link with dynamic LLVM library")
    else()
      list(REMOVE_ITEM LLVM_LIBS LTO)
      message(STATUS "Link with static LLVM libraries")
    endif()
    set(OSTAR_LLVM_VERSION ${LLVM_VERSION_MAJOR}${LLVM_VERSION_MINOR})
    set(OSTAR_INFO_LLVM_VERSION "${LLVM_VERSION_MAJOR}.${LLVM_VERSION_MINOR}.${LLVM_VERSION_PATCH}")
  else()
    # use llvm config
    message(STATUS "Use llvm-config=" ${LLVM_CONFIG})
    separate_arguments(LLVM_CONFIG)
    execute_process(COMMAND ${LLVM_CONFIG} --libfiles
      RESULT_VARIABLE __llvm_exit_code
      OUTPUT_VARIABLE __llvm_libfiles_space
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT "${__llvm_exit_code}" STREQUAL "0")
      message(FATAL_ERROR "Fatal error executing: ${LLVM_CONFIG} --libfiles")
    endif()
    execute_process(COMMAND ${LLVM_CONFIG} --system-libs
      RESULT_VARIABLE __llvm_exit_code
      OUTPUT_VARIABLE __llvm_system_libs
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT "${__llvm_exit_code}" STREQUAL "0")
      message(FATAL_ERROR "Fatal error executing: ${LLVM_CONFIG} --system-libs")
    endif()
    execute_process(COMMAND ${LLVM_CONFIG} --cxxflags
      RESULT_VARIABLE __llvm_exit_code
      OUTPUT_VARIABLE __llvm_cxxflags_space
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT "${__llvm_exit_code}" STREQUAL "0")
      message(FATAL_ERROR "Fatal error executing: ${LLVM_CONFIG} --cxxflags")
    endif()
    execute_process(COMMAND ${LLVM_CONFIG} --version
      RESULT_VARIABLE __llvm_exit_code
      OUTPUT_VARIABLE __llvm_version
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT "${__llvm_exit_code}" STREQUAL "0")
      message(FATAL_ERROR "Fatal error executing: ${LLVM_CONFIG} --version")
    endif()
    execute_process(COMMAND ${LLVM_CONFIG} --prefix
      RESULT_VARIABLE __llvm_exit_code
      OUTPUT_VARIABLE __llvm_prefix
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT "${__llvm_exit_code}" STREQUAL "0")
      message(FATAL_ERROR "Fatal error executing: ${LLVM_CONFIG} --prefix")
    endif()
    execute_process(COMMAND ${LLVM_CONFIG} --libdir
      RESULT_VARIABLE __llvm_exit_code
      OUTPUT_VARIABLE __llvm_libdir
      OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT "${__llvm_exit_code}" STREQUAL "0")
      message(FATAL_ERROR "Fatal error executing: ${LLVM_CONFIG} --libdir")
    endif()
    # map prefix => $
    # to handle the case when the prefix contains space.
    string(REPLACE ${__llvm_prefix} "$" __llvm_cxxflags ${__llvm_cxxflags_space})
    string(REPLACE ${__llvm_prefix} "$" __llvm_libfiles ${__llvm_libfiles_space})
    # llvm version
    set(OSTAR_INFO_LLVM_VERSION ${__llvm_version})
    string(REGEX REPLACE "^([^.]+)\.([^.])+\.[^.]+.*$" "\\1\\2" OSTAR_LLVM_VERSION ${__llvm_version})
    string(STRIP ${OSTAR_LLVM_VERSION} OSTAR_LLVM_VERSION)
    # definitions
    string(REGEX MATCHALL "(^| )-D[A-Za-z0-9_]*" __llvm_defs ${__llvm_cxxflags})
    set(LLVM_DEFINITIONS "")
    foreach(__flag IN ITEMS ${__llvm_defs})
      string(STRIP "${__flag}" __llvm_def)
      list(APPEND LLVM_DEFINITIONS "${__llvm_def}")
    endforeach()
    # include dir
    string(REGEX MATCHALL "(^| )-I[^ ]*" __llvm_include_flags ${__llvm_cxxflags})
    set(LLVM_INCLUDE_DIRS "")
    foreach(__flag IN ITEMS ${__llvm_include_flags})
      string(REGEX REPLACE "(^| )-I" "" __dir "${__flag}")
      # map $ => prefix
      string(REPLACE "$" ${__llvm_prefix} __dir_with_prefix "${__dir}")
      list(APPEND LLVM_INCLUDE_DIRS "${__dir_with_prefix}")
    endforeach()
    # libfiles
    set(LLVM_LIBS "")
    separate_arguments(__llvm_libfiles)
    foreach(__flag IN ITEMS ${__llvm_libfiles})
      # map $ => prefix
      string(REPLACE "$" ${__llvm_prefix} __lib_with_prefix "${__flag}")
      list(APPEND LLVM_LIBS "${__lib_with_prefix}")
    endforeach()
    separate_arguments(__llvm_system_libs)
    foreach(__flag IN ITEMS ${__llvm_system_libs})
      # If the library file ends in .lib try to
      # also search the llvm_libdir
      if(__flag MATCHES ".lib$")
        if(EXISTS "${__llvm_libdir}/${__flag}")
          set(__flag "${__llvm_libdir}/${__flag}")
        endif()
      endif()
      list(APPEND LLVM_LIBS "${__flag}")
    endforeach()
  endif()
  message(STATUS "Found LLVM_INCLUDE_DIRS=" "${LLVM_INCLUDE_DIRS}")
  message(STATUS "Found LLVM_DEFINITIONS=" "${LLVM_DEFINITIONS}")
  message(STATUS "Found LLVM_LIBS=" "${LLVM_LIBS}")
  message(STATUS "Found OSTAR_LLVM_VERSION=" ${OSTAR_LLVM_VERSION})
  if (${OSTAR_LLVM_VERSION} LESS 40)
    message(FATAL_ERROR "OSTAR requires LLVM 4.0 or higher.")
  endif()
endmacro(find_llvm)
macro(find_cuda use_cuda use_cudnn)
  set(__use_cuda ${use_cuda})
  if(${__use_cuda} MATCHES ${IS_TRUE_PATTERN})
    find_package(CUDA QUIET)
  elseif(IS_DIRECTORY ${__use_cuda})
    set(CUDA_TOOLKIT_ROOT_DIR ${__use_cuda})
    message(STATUS "Custom CUDA_PATH=" ${CUDA_TOOLKIT_ROOT_DIR})
    set(CUDA_INCLUDE_DIRS ${CUDA_TOOLKIT_ROOT_DIR}/include)
    set(CUDA_FOUND TRUE)
    if(MSVC)
      find_library(CUDA_CUDART_LIBRARY cudart
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/x64
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/Win32)
    else(MSVC)
      find_library(CUDA_CUDART_LIBRARY cudart
        ${CUDA_TOOLKIT_ROOT_DIR}/lib64
        ${CUDA_TOOLKIT_ROOT_DIR}/lib)
    endif(MSVC)
  endif()

  # additional libraries
  if(CUDA_FOUND)
    if(MSVC)
      find_library(CUDA_CUDA_LIBRARY cuda
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/x64
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/Win32)
      find_library(CUDA_NVRTC_LIBRARY nvrtc
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/x64
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/Win32)
      find_library(CUDA_CUBLAS_LIBRARY cublas
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/x64
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/Win32)
      find_library(CUDA_CUBLASLT_LIBRARY cublaslt
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/x64
        ${CUDA_TOOLKIT_ROOT_DIR}/lib/Win32)
    else(MSVC)
      find_library(_CUDA_CUDA_LIBRARY cuda
        PATHS ${CUDA_TOOLKIT_ROOT_DIR}
        PATH_SUFFIXES lib lib64 targets/x86_64-linux/lib targets/x86_64-linux/lib/stubs lib64/stubs lib/x86_64-linux-gnu
        NO_DEFAULT_PATH)
      if(_CUDA_CUDA_LIBRARY)
        set(CUDA_CUDA_LIBRARY ${_CUDA_CUDA_LIBRARY})
      endif()
      find_library(CUDA_NVRTC_LIBRARY nvrtc
        PATHS ${CUDA_TOOLKIT_ROOT_DIR}
        PATH_SUFFIXES lib lib64 targets/x86_64-linux/lib targets/x86_64-linux/lib/stubs lib64/stubs lib/x86_64-linux-gnu
        NO_DEFAULT_PATH)
      find_library(CUDA_CURAND_LIBRARY curand
        PATHS ${CUDA_TOOLKIT_ROOT_DIR}
        PATH_SUFFIXES lib lib64 targets/x86_64-linux/lib targets/x86_64-linux/lib/stubs lib64/stubs lib/x86_64-linux-gnu
        NO_DEFAULT_PATH)
      find_library(CUDA_CUBLAS_LIBRARY cublas
        PATHS ${CUDA_TOOLKIT_ROOT_DIR}
        PATH_SUFFIXES lib lib64 targets/x86_64-linux/lib targets/x86_64-linux/lib/stubs lib64/stubs lib/x86_64-linux-gnu
        NO_DEFAULT_PATH)
      # search default path if cannot find cublas in non-default
      find_library(CUDA_CUBLAS_LIBRARY cublas)
      find_library(CUDA_CUBLASLT_LIBRARY
        NAMES cublaslt cublasLt
        PATHS ${CUDA_TOOLKIT_ROOT_DIR}
        PATH_SUFFIXES lib lib64 targets/x86_64-linux/lib targets/x86_64-linux/lib/stubs lib64/stubs lib/x86_64-linux-gnu
        NO_DEFAULT_PATH)
      # search default path if cannot find cublaslt in non-default
      find_library(CUDA_CUBLASLT_LIBRARY NAMES cublaslt cublasLt)
    endif(MSVC)

    # find cuDNN
    set(__use_cudnn ${use_cudnn})
    if(${__use_cudnn} MATCHES ${IS_TRUE_PATTERN})
      set(CUDA_CUDNN_INCLUDE_DIRS ${CUDA_INCLUDE_DIRS})
      if(MSVC)
        find_library(CUDA_CUDNN_LIBRARY cudnn
          ${CUDA_TOOLKIT_ROOT_DIR}/lib/x64
          ${CUDA_TOOLKIT_ROOT_DIR}/lib/Win32)
      else(MSVC)
        find_library(CUDA_CUDNN_LIBRARY cudnn
          PATHS ${CUDA_TOOLKIT_ROOT_DIR}
          PATH_SUFFIXES lib lib64 targets/x86_64-linux/lib targets/x86_64-linux/lib/stubs lib64/stubs lib/x86_64-linux-gnu
          NO_DEFAULT_PATH)
        # search default path if cannot find cudnn in non-default
        find_library(CUDA_CUDNN_LIBRARY cudnn)
      endif(MSVC)
    elseif(IS_DIRECTORY ${__use_cudnn})
      # cuDNN doesn't necessarily live in the CUDA dir
      set(CUDA_CUDNN_ROOT_DIR ${__use_cudnn})
      set(CUDA_CUDNN_INCLUDE_DIRS ${CUDA_CUDNN_ROOT_DIR}/include)
      find_library(CUDA_CUDNN_LIBRARY cudnn
        ${CUDA_CUDNN_ROOT_DIR}/lib64
        ${CUDA_CUDNN_ROOT_DIR}/lib
        NO_DEFAULT_PATH)
    endif()

    message(STATUS "Found CUDA_TOOLKIT_ROOT_DIR=" ${CUDA_TOOLKIT_ROOT_DIR})
    message(STATUS "Found CUDA_CUDA_LIBRARY=" ${CUDA_CUDA_LIBRARY})
    message(STATUS "Found CUDA_CUDART_LIBRARY=" ${CUDA_CUDART_LIBRARY})
    message(STATUS "Found CUDA_NVRTC_LIBRARY=" ${CUDA_NVRTC_LIBRARY})
    message(STATUS "Found CUDA_CUDNN_INCLUDE_DIRS=" ${CUDA_CUDNN_INCLUDE_DIRS})
    message(STATUS "Found CUDA_CUDNN_LIBRARY=" ${CUDA_CUDNN_LIBRARY})
    message(STATUS "Found CUDA_CUBLAS_LIBRARY=" ${CUDA_CUBLAS_LIBRARY})
    message(STATUS "Found CUDA_CURAND_LIBRARY=" ${CUDA_CURAND_LIBRARY})
    message(STATUS "Found CUDA_CUBLASLT_LIBRARY=" ${CUDA_CUBLASLT_LIBRARY})
  endif(CUDA_FOUND)
endmacro(find_cuda)
if(USE_CCACHE) # True for AUTO, ON, /path/to/ccache
  if(DEFINED CMAKE_CXX_COMPILER_LAUNCHER OR DEFINED CMAKE_C_COMPILER_LAUNCHER)
    if("${USE_CCACHE}" STREQUAL "AUTO")
      message(STATUS "CMAKE_CXX_COMPILER_LAUNCHER or CMAKE_C_COMPILER_LAUNCHER already defined, not using ccache")
    elseif("${USE_CCACHE}" MATCHES ${IS_TRUE_PATTERN})
      message(FATAL_ERROR "CMAKE_CXX_COMPILER_LAUNCHER or CMAKE_C_COMPILER_LAUNCHER is already defined, refusing to override with ccache. Either unset or disable ccache.")
    endif()
  else()
    if("${USE_CCACHE}" STREQUAL "AUTO") # Auto mode
      find_program(CCACHE_FOUND "ccache")
      if(CCACHE_FOUND)
        message(STATUS "Found the path to ccache, enabling ccache")
        set(PATH_TO_CCACHE "ccache")
      else()
        message(STATUS "Didn't find the path to CCACHE, disabling ccache")
      endif(CCACHE_FOUND)
    elseif("${USE_CCACHE}" MATCHES ${IS_TRUE_PATTERN})
      find_program(CCACHE_FOUND "ccache")
      if(CCACHE_FOUND)
        message(STATUS "Found the path to ccache, enabling ccache")
        set(PATH_TO_CCACHE "ccache")
      else()
        message(FATAL_ERROR "Cannot find ccache. Set USE_CCACHE mode to AUTO or OFF to build without ccache. USE_CCACHE=" "${USE_CCACHE}")
      endif(CCACHE_FOUND)
    else()
      set(PATH_TO_CCACHE "${USE_CCACHE}")
      message(STATUS "Setting ccache path to " "${PATH_TO_CCACHE}")
    endif()
    # Set the flag for ccache
    if(DEFINED PATH_TO_CCACHE)
      set(CMAKE_CXX_COMPILER_LAUNCHER "${PATH_TO_CCACHE}")
      set(CMAKE_C_COMPILER_LAUNCHER "${PATH_TO_CCACHE}")
    endif()
  endif()
endif(USE_CCACHE)

