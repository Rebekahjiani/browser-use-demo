import unittest
from b_boundary_audit import inside


class Boundaries(unittest.TestCase):
    def test_sibling_and_prefix(self):
        root = r'C:\task\aqi\entity-extract'
        self.assertTrue(inside(root + r'\001_state\inputs\page.json', root))
        self.assertFalse(inside(r'C:\task\claudecode\entity-extract\TASK.md', root))
        self.assertFalse(inside(root + r'-other\TASK.md', root))

    def test_normalized_parent(self):
        self.assertTrue(inside(r'C:\task\.at\..\aqi\entity-extract\TASK.md', r'C:\task\aqi\entity-extract'))
        self.assertFalse(inside(r'C:\task\aqi\entity-extract\..\gold.json', r'C:\task\aqi\entity-extract'))

    def test_unresolved_relative(self):
        self.assertIsNone(inside('TASK.md', r'C:\task\aqi\entity-extract'))


if __name__ == '__main__':
    unittest.main()
