#!/usr/bin/env python3
"""Frontend build utilities for the Gecko Controller."""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class FrontendBuildUtils:
    def __init__(self, static_dir: Path, logger: Optional[logging.Logger] = None):
        self.static_dir = static_dir
        self.logger = logger or self._setup_default_logger()
        self.node_modules = static_dir / "node_modules"
        self.dist_dir = static_dir / "dist"
        self.package_json = static_dir / "package.json"
        self.package_lock = static_dir / "package-lock.json"

    def _setup_default_logger(self) -> logging.Logger:
        logger = logging.getLogger('frontend_build')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def _read_package_json(self) -> Dict[str, Any]:
        """Read and parse package.json"""
        try:
            with open(self.package_json) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading package.json: {e}")
            return {}

    def validate_environment(self) -> bool:
        """Validate Node.js environment and dependencies"""
        try:
            # Check Node.js version
            node_version = subprocess.check_output(
                ['node', '--version'],
                stderr=subprocess.STDOUT
            ).decode().strip()

            self.logger.info(f"Node.js version: {node_version}")

            # Check npm version
            npm_version = subprocess.check_output(
                ['npm', '--version'],
                stderr=subprocess.STDOUT
            ).decode().strip()

            self.logger.info(f"npm version: {npm_version}")

            # Validate package.json exists
            if not self.package_json.exists():
                self.logger.error("package.json not found")
                return False

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Environment validation failed: {e}")
            return False

        except Exception as e:
            self.logger.error(f"Unexpected error during validation: {e}")
            return False

    def install_dependencies(self, force_clean: bool = False) -> bool:
        """Install npm dependencies with fallback options"""
        try:
            if force_clean and self.node_modules.exists():
                self.logger.info("Cleaning node_modules directory...")
                shutil.rmtree(self.node_modules)

            if not self.node_modules.exists():
                if self.package_lock.exists():
                    self.logger.info("Installing dependencies using npm ci...")
                    try:
                        subprocess.run(['npm', 'ci'],
                                    check=True,
                                    cwd=self.static_dir)
                    except subprocess.CalledProcessError:
                        self.logger.warning("npm ci failed, falling back to npm install")
                        subprocess.run(['npm', 'install'],
                                    check=True,
                                    cwd=self.static_dir)
                else:
                    self.logger.info("Installing dependencies using npm install...")
                    subprocess.run(['npm', 'install'],
                                check=True,
                                cwd=self.static_dir)

            return True

        except Exception as e:
            self.logger.error(f"Dependency installation failed: {e}")
            return False

    def build_production(self) -> bool:
        """Run production build"""
        try:
            self.logger.info("Running production build...")

            # Clean dist directory
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)

            # Run build
            env = os.environ.copy()
            env['NODE_ENV'] = 'production'

            subprocess.run(
                ['npm', 'run', 'build:prod'],
                check=True,
                cwd=self.static_dir,
                env=env
            )

            # Validate build artifacts
            if not self.dist_dir.exists():
                self.logger.error("Build failed - dist directory not created")
                return False

            if not any(self.dist_dir.iterdir()):
                self.logger.error("Build failed - dist directory is empty")
                return False

            self.logger.info("Production build completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Production build failed: {e}")
            return False

    def run_development(self) -> None:
        """Start development environment"""
        try:
            self.logger.info("Starting development environment...")
            subprocess.run(
                ['npm', 'run', 'dev'],
                check=True,
                cwd=self.static_dir
            )
        except KeyboardInterrupt:
            self.logger.info("Development server stopped")
        except Exception as e:
            self.logger.error(f"Development server error: {e}")

    def validate_build(self) -> bool:
        """Validate the build artifacts"""
        try:
            if not self.dist_dir.exists():
                self.logger.error("dist directory not found")
                return False

            required_files = ['bundle.js']
            missing_files = [f for f in required_files
                           if not (self.dist_dir / f).exists()]

            if missing_files:
                self.logger.error(f"Missing required files: {', '.join(missing_files)}")
                return False

            # Validate bundle.js
            bundle_path = self.dist_dir / 'bundle.js'
            if bundle_path.stat().st_size == 0:
                self.logger.error("bundle.js is empty")
                return False

            self.logger.info("Build validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Build validation failed: {e}")
            return False

def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: frontend.py <command>")
        print("Commands: validate, install, build, dev")
        sys.exit(1)

    static_dir = Path(__file__).parent.parent.parent / "gecko_controller" / "web" / "static"
    builder = FrontendBuildUtils(static_dir)

    command = sys.argv[1]
    success = True

    if command == "validate":
        success = builder.validate_environment()
    elif command == "install":
        success = builder.install_dependencies()
    elif command == "build":
        success = builder.build_production() and builder.validate_build()
    elif command == "dev":
        builder.run_development()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
