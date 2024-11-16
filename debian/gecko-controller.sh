#!/bin/bash

VENV_DIR="/opt/gecko-controller/venv"
PYTHONPATH=/usr/lib/python3/dist-packages "$VENV_DIR/bin/python3" -m gecko_controller.controller
