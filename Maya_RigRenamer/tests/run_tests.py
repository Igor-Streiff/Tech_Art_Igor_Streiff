"""Ejecutar tests sin pytest: python -m tests.run_tests"""

from __future__ import annotations

import unittest

from tests import test_naming


def load_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_naming))
    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    raise SystemExit(not runner.run(load_suite()).wasSuccessful())
