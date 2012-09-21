import unittest

class FirstTest(unittest.TestCase):

    def test_hello(self):
        print "Hello!"

    def test_fail(self):
        self.assertEqual(1, 1)