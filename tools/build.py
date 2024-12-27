#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

class BuildError(Exception):
    """Base class for build errors"""
    pass

class FrontendBuildError(BuildError):
    """Frontend build specific errors"""
    pass

class BackendBuildError(BuildError):
    """Backend build specific errors"""
    pass

class PackagingError(BuildError):
    """Packaging specific errors"""
    pass

class BuildManager:
    def __init__(self):
        self.logger = self._setup_logging()
        # Since we're in build/scripts/, go up two levels to project root
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.build_dir = self.project_root / "build"
        self.frontend_dir = self.project_root / "gecko_controller" / "web" / "static"
        self.version = self._get_version()

        # Add debug logging for paths
        self.logger.info(f"Project root: {self.project_root}")
        self.logger.info(f"Build directory: {self.build_dir}")
        self.logger.info(f"Frontend directory: {self.frontend_dir}")

    def _setup_logging(self) -> logging.Logger:
        """Configure logging with both file and console output"""
        logger = logging.getLogger('build')
        logger.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(ch)

        # File handler
        os.makedirs('logs', exist_ok=True)
        fh = logging.FileHandler('logs/build.log')
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(fh)

        return logger

    def _get_version(self) -> str:
        """Extract version from setup.py"""
        setup_py = self.project_root / "setup.py"
        try:
            with open(setup_py, 'r') as f:
                for line in f:
                    if 'version=' in line:
                        return line.split('=')[1].strip().strip('"\'').strip()
        except Exception as e:
            self.logger.error(f"Error reading version from setup.py: {e}")
            return "0.0.0"

    def _clean_directory(self, path: Path) -> None:
        """Safely clean a directory while preserving the directory itself"""
        if path.exists():
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

    def clean(self) -> None:
        """Clean all build artifacts"""
        try:
            self.logger.info("Cleaning build artifacts...")

            # Clean Python build artifacts
            paths_to_clean = [
                self.project_root / "build",
                self.project_root / "dist",
                self.project_root / "*.egg-info",
                self.frontend_dir / "dist",
                self.frontend_dir / "node_modules"
            ]

            for path in paths_to_clean:
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    else:
                        shutil.rmtree(path)

            # Clean __pycache__ directories
            for root, dirs, files in os.walk(self.project_root):
                for d in dirs:
                    if d == "__pycache__":
                        shutil.rmtree(os.path.join(root, d))

            self.logger.info("Clean completed successfully")

        except Exception as e:
            raise BuildError(f"Clean failed: {e}")

    def build_frontend(self) -> None:
        """Build frontend assets with npm"""
        try:
            self.logger.info("Building frontend...")
            self.logger.debug(f"Frontend directory: {self.frontend_dir}")

            if not self.frontend_dir.exists():
                raise FrontendBuildError(f"Frontend directory not found: {self.frontend_dir}")

            if not (self.frontend_dir / "package.json").exists():
                raise FrontendBuildError("package.json not found in frontend directory")
            os.chdir(self.frontend_dir)

            # Ensure node_modules exists
            if not (self.frontend_dir / "node_modules").exists():
                self.logger.info("Installing npm dependencies...")
                try:
                    subprocess.run(['npm', 'ci'], check=True)
                except subprocess.CalledProcessError:
                    self.logger.warning("npm ci failed, falling back to npm install")
                    subprocess.run(['npm', 'install'], check=True)

            # Build production assets
            self.logger.info("Running production build...")
            subprocess.run(['npm', 'run', 'build:prod'], check=True)

            # Validate build artifacts
            dist_dir = self.frontend_dir / "dist"
            if not dist_dir.exists() or not any(dist_dir.iterdir()):
                raise FrontendBuildError("Frontend build failed - no artifacts produced")

            self.logger.info("Frontend build completed successfully")

        except Exception as e:
            raise FrontendBuildError(f"Frontend build failed: {e}")
        finally:
            os.chdir(self.project_root)

    def build_backend(self) -> None:
        """Build Python package"""
        try:
            self.logger.info("Building backend...")

            # Create source distribution
            subprocess.run([sys.executable, 'setup.py', 'sdist'], check=True)

            # Validate build artifacts
            dist_dir = self.project_root / "dist"
            if not dist_dir.exists() or not any(dist_dir.iterdir()):
                raise BackendBuildError("Backend build failed - no artifacts produced")

            self.logger.info("Backend build completed successfully")

        except Exception as e:
            raise BackendBuildError(f"Backend build failed: {e}")

    def run_tests(self) -> None:
        """Run test suite"""
        try:
            self.logger.info("Running tests...")
            subprocess.run(['python3', '-m', 'pytest', 'tests/'], check=True)
            self.logger.info("Tests completed successfully")
        except subprocess.CalledProcessError as e:
            raise BuildError(f"Tests failed with exit code {e.returncode}")

    def build_package(self) -> None:
        """Build Debian package"""
        try:
            self.logger.info("Building Debian package...")

            # Build package using debuild
            subprocess.run([
                'debuild',
                '--no-lintian',
                '--no-sign',
                '-uc',
                '-us'
            ], check=True)

            # Verify package was created
            package_name = f"gecko-controller_{self.version}_all.deb"
            package_path = self.project_root.parent / package_name

            if not package_path.exists():
                raise PackagingError(f"Package {package_name} was not created")

            self.logger.info(f"Package built successfully: {package_name}")

        except Exception as e:
            raise PackagingError(f"Package build failed: {e}")

    def run(self, command: str) -> None:
        """Main entry point for build commands"""
        commands = {
            'clean': self.clean,
            'frontend': self.build_frontend,
            'backend': self.build_backend,
            'test': self.run_tests,
            'package': self.build_package,
        }

        if command not in commands:
            raise ValueError(f"Unknown command: {command}")

        try:
            commands[command]()
        except BuildError as e:
            self.logger.error(f"Build failed: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: build.py <command>")
        print("Commands: clean, frontend, backend, test, package")
        sys.exit(1)

    manager = BuildManager()
    manager.run(sys.argv[1])

if __name__ == "__main__":
    main()
