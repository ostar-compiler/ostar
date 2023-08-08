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
