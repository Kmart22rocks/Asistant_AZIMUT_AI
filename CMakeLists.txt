cmake_minimum_required(VERSION 3.24)
project(Asistant_AZIMUT_II LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_PREFIX_PATH "D:/Qt-data/6.12.0/mingw_64")

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network)

add_executable(Asistant_AZIMUT_II
        src_cpp/main.cpp
        src_cpp/core/ProcessManager.h
        src_cpp/core/ProcessManager.cpp
        src_cpp/network/KompasBridge.h
        src_cpp/network/KompasBridge.cpp
        src_cpp/network/OllamaClient.h
        src_cpp/network/OllamaClient.cpp
        src_cpp/ui/StatusIndicator.h
        src_cpp/ui/StatusIndicator.cpp
        src_cpp/ui/MainWindow.h
        src_cpp/ui/MainWindow.cpp
)

target_include_directories(Asistant_AZIMUT_II PRIVATE src_cpp)

target_link_libraries(Asistant_AZIMUT_II PRIVATE
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
        Qt6::Network
)

add_library(AzimutPlugin SHARED
        src_cpp/plugin/kompas_plugin.cpp
        src_cpp/plugin/kompas_plugin.def
)

set_target_properties(AzimutPlugin PROPERTIES
        PREFIX ""
        SUFFIX ".rtw"
)

target_link_options(AzimutPlugin PRIVATE -static -static-libgcc -static-libstdc++)