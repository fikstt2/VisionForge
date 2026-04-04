import unittest
import sys
import os

if __name__ == '__main__':
    # Add root folder to Path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        sys.exit(1)
