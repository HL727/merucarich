from django.test import TestCase

from unittest.mock import patch, MagicMock

from asyncworker import asynchelpers

class AsyncWorkerTests(TestCase):
    
    def test_reached_maximum_sequence(self):
        with patch('asyncworker.tests.asynchelpers.settings') as m:
            # return False whenever
            m.ASYNC_WORKER = {'MAXIMUM_SEQUENCE': 0}
            self.assertFalse(asynchelpers.reached_maximum_sequence(-1))
            self.assertFalse(asynchelpers.reached_maximum_sequence(0))
            self.assertFalse(asynchelpers.reached_maximum_sequence(1))

        with patch('asyncworker.tests.asynchelpers.settings') as m:
            m.ASYNC_WORKER = {'MAXIMUM_SEQUENCE': 3}
            self.assertFalse(asynchelpers.reached_maximum_sequence(-1))
            self.assertFalse(asynchelpers.reached_maximum_sequence(0))
            self.assertFalse(asynchelpers.reached_maximum_sequence(2))
            self.assertTrue(asynchelpers.reached_maximum_sequence(3))

