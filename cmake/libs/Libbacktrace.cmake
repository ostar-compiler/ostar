include(ExternalProject)


if(CMAKE_SYSTEM_NAME MATCHES "Darwin" AND (CMAKE_C_COMPILER MATCHES "^/Library"
  OR CMAKE_C_COMPILER MATCHES "^/Applications"))
    set(c_compiler "/usr/bin/cc")
  else()
    set(c_compiler "${CMAKE_C_COMPILER}")
endif()

ExternalProject_Add(project_libbacktrace
  PREFIX libbacktrace
  SOURCE_DIR ${CMAKE_CURRENT_LIST_DIR}/../../3rdparty/libbacktrace
  BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR}/libbacktrace
  CONFIGURE_COMMAND "${CMAKE_CURRENT_LIST_DIR}/../../3rdparty/libbacktrace/configure"
                    "--prefix=${CMAKE_CURRENT_BINARY_DIR}/libbacktrace"
                    --with-pic
                    "CC=${c_compiler}"
                    "CFLAGS=${CMAKE_C_FLAGS}"
                    "LDFLAGS=${CMAKE_EXE_LINKER_FLAGS}"
                    "CPP=${c_compiler} -E"
                    "NM=${CMAKE_NM}"
                    "STRIP=${CMAKE_STRIP}"
                    "--host=${MACHINE_NAME}"
  INSTALL_DIR "${CMAKE_CURRENT_BINARY_DIR}/libbacktrace"
  BUILD_COMMAND make
  INSTALL_COMMAND make install
  BUILD_BYPRODUCTS "${CMAKE_CURRENT_BINARY_DIR}/libbacktrace/lib/libbacktrace.a"
                   "${CMAKE_CURRENT_BINARY_DIR}/libbacktrace/include/backtrace.h"
  )

# Custom step to rebuild libbacktrace if any of the source files change
ostar_file_glob(GLOB LIBBACKTRACE_SRCS "${CMAKE_CURRENT_LIST_DIR}/../../3rdparty/libbacktrace/*.c")
ExternalProject_Add_Step(project_libbacktrace checkout
  DEPENDERS configure
  DEPENDEES download
  DEPENDS ${LIBBACKTRACE_SRCS}
)

# create include directory so cmake doesn't complain
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/libbacktrace/include)
