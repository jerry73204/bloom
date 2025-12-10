#!/usr/bin/make -f
# -*- makefile -*-
# Sample debian/rules that uses debhelper.
# This file was originally written by Joey Hess and Craig Small.
# As a special exception, when this file is copied by dh-make into a
# dh-make output file, you may use that output file without restriction.
# This special exception was added by Craig Small in version 0.37 of dh-make.

# Use bash for all shell commands (required for sourcing colcon setup.bash)
SHELL := /bin/bash

# Uncomment this to turn on verbose mode.
export DH_VERBOSE=1
# TODO: remove the LDFLAGS override.  It's here to avoid esoteric problems
# of this sort:
#  https://code.ros.org/trac/ros/ticket/2977
#  https://code.ros.org/trac/ros/ticket/3842
export LDFLAGS=
export PKG_CONFIG_PATH=@(InstallationPrefix)/lib/pkgconfig
# Explicitly enable -DNDEBUG, see:
# 	https://github.com/ros-infrastructure/bloom/issues/327
export DEB_CXXFLAGS_MAINT_APPEND=-DNDEBUG
ifneq ($(filter nocheck,$(DEB_BUILD_OPTIONS)),)
	BUILD_TESTING_ARG=-DBUILD_TESTING=OFF
endif

DEB_HOST_GNU_TYPE ?= $(shell dpkg-architecture -qDEB_HOST_GNU_TYPE)

# Colcon workspace install path (set by colcon2deb, defaults to empty)
COLCON_INSTALL_PATH ?= @(ColconInstallPath)

# ROS base path (where ROS2 is installed, e.g. /opt/ros/humble)
ROS_BASE_PATH ?= /opt/ros/humble

# Build combined prefix paths as a proper CMake list (semicolon-separated)
# Note: We construct this path carefully to work with cmake's list format
ifneq ($(COLCON_INSTALL_PATH),)
	PATH_COLCON = $(COLCON_INSTALL_PATH)
	PATH_INSTALL = @(InstallationPrefix)
	PATH_ROS = $(ROS_BASE_PATH)
	# Use local_setup.bash to avoid chaining to other prefixes
	SETUP_SCRIPT = $(COLCON_INSTALL_PATH)/local_setup.bash
else
	PATH_COLCON =
	PATH_INSTALL = @(InstallationPrefix)
	PATH_ROS = $(ROS_BASE_PATH)
	SETUP_SCRIPT = @(InstallationPrefix)/local_setup.bash
endif

# Export CMAKE_PREFIX_PATH and AMENT_PREFIX_PATH as environment variables
# These will be inherited by cmake when dh_auto_configure runs
export CMAKE_PREFIX_PATH := $(PATH_COLCON):$(PATH_INSTALL):$(PATH_ROS)
export AMENT_PREFIX_PATH := $(PATH_COLCON):$(PATH_INSTALL):$(PATH_ROS)

%:
	dh $@@ -v --buildsystem=cmake --builddirectory=.obj-$(DEB_HOST_GNU_TYPE)

override_dh_auto_configure:
	# Source the colcon workspace local_setup.bash first to get any additional env vars
	# Set CMAKE_PREFIX_PATH and AMENT_PREFIX_PATH as environment variables with semicolons
	# cmake will use these env vars if the cache vars are not set
	source "$(SETUP_SCRIPT)" 2>/dev/null || true && \
	export CMAKE_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	export AMENT_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	mkdir -p .obj-$(DEB_HOST_GNU_TYPE) && \
	cd .obj-$(DEB_HOST_GNU_TYPE) && \
	cmake .. \
		-DCMAKE_INSTALL_PREFIX=@(InstallationPrefix) \
		-DCMAKE_BUILD_TYPE=None \
		-DCMAKE_VERBOSE_MAKEFILE=ON \
		-DCMAKE_INSTALL_LIBDIR=lib/$(DEB_HOST_GNU_TYPE) \
		$(BUILD_TESTING_ARG)

override_dh_auto_build:
	# Source setup script for build environment
	source "$(SETUP_SCRIPT)" 2>/dev/null || true && \
	export CMAKE_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	export AMENT_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	$(MAKE) -C .obj-$(DEB_HOST_GNU_TYPE)

override_dh_auto_test:
	# Source setup script for test environment
	echo "-- Running tests. Even if one of them fails the build is not canceled."
	source "$(SETUP_SCRIPT)" 2>/dev/null || true && \
	export CMAKE_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	export AMENT_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	$(MAKE) -C .obj-$(DEB_HOST_GNU_TYPE) test || true

override_dh_shlibdeps:
	# Source setup script for shared library dependency resolution
	source "$(SETUP_SCRIPT)" 2>/dev/null || true; \
	dh_shlibdeps $(EXTRA_LIB_PATHS) -l$(CURDIR)/debian/@(Package)/@(InstallationPrefix)/lib/:$(CURDIR)/debian/@(Package)/@(InstallationPrefix)/opt/@(Name)/lib/

override_dh_auto_install:
	# Source setup script for install environment
	source "$(SETUP_SCRIPT)" 2>/dev/null || true && \
	export CMAKE_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	export AMENT_PREFIX_PATH='$(PATH_COLCON);$(PATH_INSTALL);$(PATH_ROS)' && \
	DESTDIR=$(CURDIR)/debian/@(Package) $(MAKE) -C .obj-$(DEB_HOST_GNU_TYPE) install
