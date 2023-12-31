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
