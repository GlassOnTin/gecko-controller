# Gecko Controller Build System
PYTHON := python3
BUILD_SCRIPT := tools/build.py

.PHONY: all clean build test package build-frontend build-backend

all: clean build test package

clean:
	$(PYTHON) $(BUILD_SCRIPT) clean

build: build-frontend build-backend

build-frontend:
	$(PYTHON) $(BUILD_SCRIPT) frontend

build-backend:
	$(PYTHON) $(BUILD_SCRIPT) backend

test:
	$(PYTHON) $(BUILD_SCRIPT) test

package:
	$(PYTHON) $(BUILD_SCRIPT) package

# Development targets
.PHONY: dev install-deps

dev: install-deps
	cd gecko_controller/web/static && npm run dev

install-deps:
	$(PYTHON) -m pip install -r build/config/requirements.txt
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
