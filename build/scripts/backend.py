#!/usr/bin/env python3
"""Backend build utilities for the Gecko Controller."""

import os
import sys
import venv
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
import logging
import pkg_resources

class BackendBuildUtils:
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
def __init__(self, project_root: Path, logger: Optional[logging.Logger] = None):
        self.project_root = project_root
        self.logger = logger or self._setup_default_logger()
        self.build_dir = project_root / "build"
        self.dist_dir = project_root / "dist"
        self.venv_dir = project_root / ".venv"
        self.requirements_file = self.build_dir / "config" / "requirements.txt"

    def _setup_default_logger(self) -> logging.Logger:
        logger = logging.getLogger('backend_build')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def setup_virtual_environment(self, force_recreate: bool = False) -> bool:
        """Create or update virtual environment"""
        try:
            if force_recreate and self.venv_dir.exists():
                self.logger.info("Removing existing virtual environment...")
                shutil.rmtree(self.venv_dir)

            if not self.venv_dir.exists():
                self.logger.info("Creating virtual environment...")
                venv.create(self.venv_dir, with_pip=True)

            # Get paths
            if os.name == 'nt':  # Windows
                python_path = self.venv_dir / "Scripts" / "python.exe"
                pip_path = self.venv_dir / "Scripts" / "pip.exe"
            else:  # Unix
                python_path = self.venv_dir / "bin" / "python"
                pip_path = self.venv_dir / "bin" / "pip"

            # Upgrade pip
            subprocess.run([str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip'],
                         check=True)

            # Install requirements if they exist
            if self.requirements_file.exists():
                self.logger.info("Installing requirements...")
                subprocess.run([str(pip_path), 'install', '-r', str(self.requirements_file)],
                             check=True)

            return True

        except Exception as e:
            self.logger.error(f"Virtual environment setup failed: {e}")
            return False

    def validate_python_environment(self) -> bool:
        """Validate Python environment and dependencies"""
        try:
            # Check Python version
            python_version = sys.version.split()[0]
            self.logger.info(f"Python version: {python_version}")

            # Check required dependencies
            if self.requirements_file.exists():
                missing_deps = self._check_dependencies()
                if missing_deps:
                    self.logger.error(f"Missing dependencies: {', '.join(missing_deps)}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Environment validation failed: {e}")
            return False

    def _check_dependencies(self) -> List[str]:
        """Check for missing dependencies"""
        missing = []
        if self.requirements_file.exists():
            with open(self.requirements_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            req = pkg_resources.Requirement.parse(line)
                            pkg_resources.working_set.find(req)
                        except:
                            missing.append(line)
        return missing

    def build_package(self) -> bool:
        """Build Python package"""
        try:
            self.logger.info("Building Python package...")

            # Clean previous builds
            for path in [self.build_dir, self.dist_dir]:
                if path.exists():
                    shutil.rmtree(path)

            # Run setup.py
            subprocess.run(
                [sys.executable, 'setup.py', 'sdist', 'bdist_wheel'],
                check=True,
                cwd=self.project_root
            )

            if not self.dist_dir.exists() or not any(self.dist_dir.iterdir()):
                self.logger.error("Build failed - no artifacts produced")
                return False

            self.logger.info("Package build completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Package build failed: {e}")
            return False

    def validate_build(self) -> bool:
        """Validate build artifacts"""
        try:
            if not self.dist_dir.exists():
                self.logger.error("dist directory not found")
                return False

            # Check for both source distribution and wheel
            sdist_files = list(self.dist_dir.glob('*.tar.gz'))
            wheel_files = list(self.dist_dir.glob('*.whl'))

            if not sdist_files:
                self.logger.error("Source distribution not found")
                return False

            if not wheel_files:
                self.logger.error("Wheel distribution not found")
                return False

            # Validate file sizes
            for f in sdist_files + wheel_files:
                if f.stat().st_size == 0:
                    self.logger.error(f"{f.name} is empty")
                    return False

            self.logger.info("Build validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Build validation failed: {e}")
            return False

    def run_tests(self, coverage: bool = False) -> bool:
        """Run test suite"""
        try:
            self.logger.info("Running tests...")
            cmd = ['pytest']

            if coverage:
                cmd.extend(['--cov=gecko_controller', '--cov-report=html'])

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.logger.error(f"Tests failed:\n{result.stdout}\n{result.stderr}")
                return False

            self.logger.info("Tests completed successfully")
            if coverage:
                self.logger.info("Coverage report generated in htmlcov/")

            return True

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return False

def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: backend.py <command>")
        print("Commands: validate, venv, build, test")
        sys.exit(1)

    project_root = Path(__file__).parent.parent.parent
    builder = BackendBuildUtils(project_root)

    command = sys.argv[1]
    success = True

    if command == "validate":
        success = builder.validate_python_environment()
    elif command == "venv":
        success = builder.setup_virtual_environment()
    elif command == "build":
        success = builder.build_package() and builder.validate_build()
    elif command == "test":
        success = builder.run_tests(coverage=True)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
