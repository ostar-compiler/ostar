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
