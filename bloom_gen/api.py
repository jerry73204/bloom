# Software License Agreement (BSD License)
#
# Copyright (c) 2024, colcon2deb contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Library API for bloom debian generation.

This module provides a clean API for generating Debian packaging metadata
from ROS packages without using shell commands.

Example usage:
    from bloom_gen.api import generate_debian

    result = generate_debian(
        package_path="/path/to/ros_package",
        ros_distro="humble",
        os_name="ubuntu",
        os_version="jammy",
        install_prefix="/opt/ros/humble",
        colcon_install_path="/path/to/colcon/install",
    )
    if result.success:
        print(f"Debian files generated in {result.debian_dir}")
    else:
        print(f"Error: {result.error}")
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GenerateResult:
    """Result of debian generation."""
    success: bool
    debian_dir: Optional[Path] = None
    package_name: Optional[str] = None
    error: Optional[str] = None


def generate_debian(
    package_path: str | Path,
    ros_distro: str,
    os_name: str = "ubuntu",
    os_version: str = "jammy",
    install_prefix: Optional[str] = None,
    colcon_install_path: Optional[str] = None,
    debian_inc: str = "0",
    native: bool = False,
) -> GenerateResult:
    """
    Generate Debian packaging metadata for a ROS package.

    Args:
        package_path: Path to the ROS package (containing package.xml)
        ros_distro: ROS distribution (e.g., "humble", "iron")
        os_name: Operating system name (default: "ubuntu")
        os_version: OS version/codename (default: "jammy")
        install_prefix: Installation prefix (default: /opt/ros/{ros_distro})
        colcon_install_path: Path to colcon install directory (for CMAKE_PREFIX_PATH)
        debian_inc: Debian increment number (default: "0")
        native: Whether to generate native package (default: False)

    Returns:
        GenerateResult with success status and debian directory path or error message.
    """
    package_path = Path(package_path)

    # Set environment variables for templates
    if install_prefix is None:
        install_prefix = f"/opt/ros/{ros_distro}"

    os.environ['ROS_DISTRO'] = ros_distro
    os.environ['InstallationPrefix'] = install_prefix
    if colcon_install_path:
        os.environ['COLCON_INSTALL_PATH'] = colcon_install_path

    try:
        # Import bloom modules here to avoid import errors during module load
        from catkin_pkg.packages import find_packages

        from bloom_gen.generators.debian.generator import (
            generate_substitutions_from_package,
            place_template_files,
            process_template_files,
        )
        from bloom_gen.generators.rosdebian import rosify_package_name

        # Find package
        pkgs_dict = find_packages(str(package_path))
        if len(pkgs_dict) == 0:
            return GenerateResult(
                success=False,
                error=f"No packages found in path: '{package_path}'"
            )
        if len(pkgs_dict) > 1:
            return GenerateResult(
                success=False,
                error="Multiple packages found, this tool only supports one package at a time."
            )

        # Get package
        path, pkg = list(pkgs_dict.items())[0]
        pkg_path = package_path / path if path != '.' else package_path

        # Generate substitutions
        subs = generate_substitutions_from_package(
            pkg,
            os_name,
            os_version,
            ros_distro,
            install_prefix,
            deb_inc=debian_inc,
            native=native,
        )

        # Rosify package name (ros-{distro}-{name})
        subs['Package'] = rosify_package_name(subs['Package'], ros_distro)
        subs['Rosdistro'] = ros_distro

        # Place template files based on build type
        build_type = pkg.get_build_type()
        place_template_files(str(pkg_path), build_type, gbp=False)

        # Process templates
        template_files = process_template_files(str(pkg_path), subs)

        # Remove template files after processing
        if template_files:
            for template_file in template_files:
                try:
                    os.remove(os.path.normpath(template_file))
                except OSError:
                    pass

        debian_dir = pkg_path / "debian"
        return GenerateResult(
            success=True,
            debian_dir=debian_dir,
            package_name=pkg.name,
        )

    except Exception as e:
        import traceback
        return GenerateResult(
            success=False,
            error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        )


def copy_debian_to_dest(
    src_debian_dir: Path,
    dst_debian_dir: Path,
) -> GenerateResult:
    """
    Copy debian directory from source to destination.

    Args:
        src_debian_dir: Source debian directory
        dst_debian_dir: Destination debian directory

    Returns:
        GenerateResult with success status.
    """
    try:
        if dst_debian_dir.exists():
            shutil.rmtree(dst_debian_dir)
        shutil.copytree(src_debian_dir, dst_debian_dir)
        return GenerateResult(
            success=True,
            debian_dir=dst_debian_dir,
        )
    except Exception as e:
        return GenerateResult(
            success=False,
            error=f"Failed to copy debian directory: {e}"
        )
