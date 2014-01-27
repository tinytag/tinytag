import sys

if sys.version_info[0] > 2:
    import unittest
else:
    import unittest2 as unittest

if __name__ == '__main__':
    unittest.main()
