# Created by the script cgal_create_CMakeLists
# This is the CMake script for compiling a set of CGAL applications.

cmake_minimum_required(VERSION 3.1...3.23)
project(Classification_Examples)

# CGAL and its components
find_package(CGAL REQUIRED)

set(Classification_dependencies_met TRUE)

find_package(Boost OPTIONAL_COMPONENTS serialization iostreams)
include(CGAL_Boost_serialization_support)
include(CGAL_Boost_iostreams_support)

if(NOT TARGET CGAL::Boost_serialization_support)
  message("NOTICE: This project requires Boost Serialization, and will not be compiled.")
  set(Classification_dependencies_met FALSE)
endif()

if(NOT TARGET CGAL::Boost_iostreams_support)
  message("NOTICE: This project requires Boost IO Streams, and will not be compiled.")
  set(Classification_dependencies_met FALSE)
endif()

find_package(Eigen3 3.1.0 QUIET) #(3.1.0 or greater)
include(CGAL_Eigen3_support)
if(NOT TARGET CGAL::Eigen3_support)
  message("NOTICE: This project requires the Eigen library, and will not be compiled.")
  set(Classification_dependencies_met FALSE)
endif()

if(NOT Classification_dependencies_met)
  return()
endif()

#Add LASlib
add_subdirectory(LAStools)

find_package(TBB QUIET)
include(CGAL_TBB_support)

create_single_source_cgal_program( "example_classification.cpp" )
create_single_source_cgal_program( "example_alphawrap.cpp" )

foreach(target
    example_classification
    example_alphawrap)
  if(TARGET ${target})
    target_link_libraries(${target} PUBLIC CGAL::Eigen3_support
                                           CGAL::Boost_iostreams_support
                                           CGAL::Boost_serialization_support
                                           LASlib
                                           )
    if(TARGET CGAL::TBB_support)
      target_link_libraries(${target} PUBLIC CGAL::TBB_support)
    endif()
  endif()
endforeach()
