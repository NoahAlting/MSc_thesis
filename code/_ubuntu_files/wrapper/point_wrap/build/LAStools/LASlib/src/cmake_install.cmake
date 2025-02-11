# Install script for directory: /home/noah/point_wrap/LAStools/LASlib/src

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/LASlib" TYPE FILE FILES
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/arithmeticdecoder.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/arithmeticencoder.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/arithmeticmodel.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamin.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamin_array.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamin_file.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamin_istream.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreaminout.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreaminout_file.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamout.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamout_array.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamout_file.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamout_nil.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/bytestreamout_ostream.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/integercompressor.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasattributer.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasindex.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasinterval.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laspoint.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasquadtree.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasquantizer.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreaditem.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreaditemcompressed_v1.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreaditemcompressed_v2.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreaditemcompressed_v3.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreaditemcompressed_v4.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreaditemraw.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/lasreadpoint.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswriteitem.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswriteitemcompressed_v1.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswriteitemcompressed_v2.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswriteitemcompressed_v3.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswriteitemcompressed_v4.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswriteitemraw.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laswritepoint.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laszip.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laszip_common_v1.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laszip_common_v2.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laszip_common_v3.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/laszip_decompress_selective_v3.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../../LASzip/src/mydefs.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasdefinitions.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasfilter.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasignore.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laskdtree.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_asc.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_bil.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_bin.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_dtm.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_las.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_ply.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_qfit.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_shp.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreader_txt.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreaderbuffered.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreadermerged.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreaderpipeon.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasreaderstored.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lastransform.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasutility.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasvlr.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/lasvlrpayload.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswaveform13reader.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswaveform13writer.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswriter.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswriter_bin.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswriter_las.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswriter_qfit.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswriter_txt.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswriter_wrl.hpp"
    "/home/noah/point_wrap/LAStools/LASlib/src/../inc/laswritercompatible.hpp"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/LASlib" TYPE STATIC_LIBRARY FILES "/home/noah/point_wrap/LAStools/LASlib/lib/libLASlib.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib/laslib-targets.cmake")
    file(DIFFERENT _cmake_export_file_changed FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib/laslib-targets.cmake"
         "/home/noah/point_wrap/build/LAStools/LASlib/src/CMakeFiles/Export/c55326e5cb745217e14af8383b523273/laslib-targets.cmake")
    if(_cmake_export_file_changed)
      file(GLOB _cmake_old_config_files "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib/laslib-targets-*.cmake")
      if(_cmake_old_config_files)
        string(REPLACE ";" ", " _cmake_old_config_files_text "${_cmake_old_config_files}")
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib/laslib-targets.cmake\" will be replaced.  Removing files [${_cmake_old_config_files_text}].")
        unset(_cmake_old_config_files_text)
        file(REMOVE ${_cmake_old_config_files})
      endif()
      unset(_cmake_old_config_files)
    endif()
    unset(_cmake_export_file_changed)
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib" TYPE FILE FILES "/home/noah/point_wrap/build/LAStools/LASlib/src/CMakeFiles/Export/c55326e5cb745217e14af8383b523273/laslib-targets.cmake")
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^()$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib" TYPE FILE FILES "/home/noah/point_wrap/build/LAStools/LASlib/src/CMakeFiles/Export/c55326e5cb745217e14af8383b523273/laslib-targets-noconfig.cmake")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/LASlib" TYPE FILE FILES "/home/noah/point_wrap/LAStools/LASlib/src/laslib-config.cmake")
endif()

