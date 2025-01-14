cmake_minimum_required(VERSION 3.10)
project(test)

# # Set C++ standard
set(CMAKE_CXX_STANDARD 17)

# # Add source files
set(SOURCES
    # test.cpp
    TreeSeparation/Source.cpp
    TreeSeparation/FoxTree.cpp
)

# # Add executable target
# add_executable(tree_separator ${SOURCES})
add_executable(tree_test ${SOURCES})
