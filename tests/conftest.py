import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--hardware",
        action="store_true",
        default=False,
        help="run tests that require hardware"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "hardware: mark test as requiring hardware")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--hardware"):
        # --hardware given in cli: do not skip hardware tests
        return
    skip_hardware = pytest.mark.skip(reason="need --hardware option to run")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hardware)
