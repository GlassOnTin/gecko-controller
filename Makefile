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
.PHONY: dev install-deps

dev: install-deps
	cd gecko_controller/web/static && npm run dev

install-deps: $(VENV)/bin/activate
	cd gecko_controller/web/static && npm install

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
