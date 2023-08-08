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
