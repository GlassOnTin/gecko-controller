# Makefile
SHELL := /bin/bash
PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
PYTHON_VENV := $(VENV)/bin/python

.PHONY: all clean build test package build-frontend build-backend

all: clean build test package

clean: clean-venv
	$(PYTHON) tools/build.py clean

build: build-frontend build-backend

build-frontend:
	$(PYTHON) tools/build.py frontend

build-backend:
	$(PYTHON) tools/build.py backend

test: activate
	$(PYTEST) tests/

activate: $(VENV)/bin/activate
	source $(VENV)/bin/activate
$(VENV)/bin/activate:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(PIP) install -e ".[test]"

package:
	$(PYTHON) tools/build.py package

# Development targets
.PHONY: quick-update quick-restart logs logs-web

# Location of installed package
INSTALL_DIR := /usr/lib/python3/dist-packages/gecko_controller

# Quick update - copy changed files and restart services
quick-update:
	@echo "Stopping services..."
	sudo systemctl stop gecko-web gecko-controller
	@echo "Copying updated files..."
	sudo cp gecko_controller/display_socket.py $(INSTALL_DIR)/
	# Add any other files you frequently modify:
	sudo cp gecko_controller/controller.py $(INSTALL_DIR)/
	sudo cp gecko_controller/web/app.py $(INSTALL_DIR)/web/
	@echo "Starting services..."
	sudo systemctl restart gecko-controller
	sudo systemctl restart gecko-web
	@echo "Done. Use 'make logs' to watch the logs"

# Just restart the services
quick-restart:
	sudo systemctl restart gecko-controller
	sudo systemctl restart gecko-web

# Watch the logs
logs:
	journalctl -fu gecko-controller
logs-web:
	journalctl -fu gecko-web

# Utility targets
.PHONY: version-check version-bump

version-check:
	./tools/verify-versions.sh

version-bump:
	./tools/bump-version.sh

# Help target
.PHONY: help
help:
	@echo "Gecko Controller Build System"
	@echo ""
	@echo "Main targets:"
	@echo "  all          - Clean, build, test, and package"
	@echo "  clean        - Remove all build artifacts"
	@echo "  build        - Build frontend and backend"
	@echo "  test         - Run test suite"
	@echo "  package      - Create Debian package"
	@echo ""
	@echo "Development targets:"
	@echo "  dev          - Start development environment"
	@echo "  install-deps - Install all dependencies"
	@echo ""
	@echo "Utility targets:"
	@echo "  version-check - Verify version consistency"
	@echo "  version-bump  - Bump version numbers"

# Clean virtual environment
.PHONY: clean-venv
clean-venv:
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
