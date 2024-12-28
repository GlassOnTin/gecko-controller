#!/usr/bin/env python3
"""Packaging utilities for the Gecko Controller."""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from datetime import datetime

class PackagingUtils:
    def __init__(self, project_root: Path, logger: Optional[logging.Logger] = None):
        self.project_root = project_root
        self.logger = logger or self._setup_default_logger()
        self.debian_dir = project_root / "debian"
        self.version = self._get_version()

    def _setup_default_logger(self) -> logging.Logger:
        logger = logging.getLogger('packaging')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def _get_version(self) -> str:
        """Extract version from setup.py"""
        setup_py = self.project_root / "setup.py"
        try:
            with open(setup_py, 'r') as f:
                for line in f:
                    if 'version=' in line:
                        version = line.split('version=')[1].strip().strip(',').strip('"\'')
                        print(f"Extracted version: {version}")  # Debugging
                        return version
            self.logger.error("Version not found in setup.py")
            return "0.0.0"
        except Exception as e:
            self.logger.error(f"Error reading version: {e}")
            return "0.0.0"

    def validate_debian_files(self) -> bool:
        """Validate presence and content of debian packaging files"""
        try:
            required_files = [
                'control',
                'rules',
                'compat',
                'changelog',
                'install',
                'gecko-controller.service'
            ]

            for file in required_files:
                file_path = self.debian_dir / file
                if not file_path.exists():
                    self.logger.error(f"Missing required file: {file}")
                    return False
                if file_path.stat().st_size == 0:
                    self.logger.error(f"File is empty: {file}")
                    return False

            # Validate changelog format
            result = subprocess.run(
                ['dpkg-parsechangelog'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.logger.error("Invalid changelog format")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Debian files validation failed: {e}")
            return False

    def _prepare_build_environment(self) -> bool:
        """Prepare environment for package building"""
        try:
            # Check for required tools
            required_tools = ['debuild', 'dpkg-buildpackage', 'dh_make']
            for tool in required_tools:
                if not shutil.which(tool):
                    self.logger.error(f"Required tool not found: {tool}")
                    return False

            # Create necessary directories
            os.makedirs(self.debian_dir / "source", exist_ok=True)

            # Ensure correct permissions
            subprocess.run(['chmod', '+x', str(self.debian_dir / "rules")])

            return True

        except Exception as e:
            self.logger.error(f"Build environment preparation failed: {e}")
            return False

    def build_package(self, no_sign: bool = True) -> bool:
        """Build Debian package"""
        try:
            if not self._prepare_build_environment():
                return False

            self.logger.info("Building Debian package...")

            # Build command
            cmd = ['dpkg-buildpackage', '-us', '-uc']  # Use dpkg-buildpackage directly
            if no_sign:
                cmd.extend(['-us', '-uc'])
            cmd.append('-b')  # Binary-only build

            # Run build
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Stream output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.logger.info(output.strip())

            if process.returncode != 0:
                stderr = process.stderr.read()
                self.logger.error(f"Package build failed:\n{stderr}")
                return False

            # Determine the architecture from debian/control
            control_file = self.debian_dir / "control"
            architecture = "all"  # Default to "all"
            try:
                with open(control_file, 'r') as f:
                    for line in f:
                        if line.startswith('Architecture:'):
                            architecture = line.split(':', 1)[1].strip()
                            break
            except Exception as e:
                self.logger.warning(f"Failed to read debian/control: {e}. Using default architecture 'all'.")

            # Verify package was created
            package_name = f"gecko-controller_{self.version}_{architecture}.deb"
            package_path = self.project_root.parent / package_name

            if not package_path.exists():
                self.logger.error(f"Package file not found: {package_name}")
                return False

            self.logger.info(f"Successfully built package: {package_name}")
            return True

        except Exception as e:
            self.logger.error(f"Package build failed: {e}")
            return False

def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: package.py <command>")
        print("Commands: validate, build, test")
        sys.exit(1)

    project_root = Path(__file__).parent.parent.parent
    packager = PackagingUtils(project_root)

    command = sys.argv[1]
    success = True

    if command == "validate":
        success = packager.validate_debian_files()
    elif command == "build":
        success = packager.build_package()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
