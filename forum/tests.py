import unittest
from django.test.client import Client

import forum.startup

from forum.models import *
from forum.actions import *

client = Client()

class SanityTest(unittest.TestCase):
    def testIndex(self):
        self.assertEquals(client.get('/').status_code, 200)

class FirstUsersTest(unittest.TestCase):
    def setUp(self):
        self.response = client.get('/')

    def testResponse(self):
        self.assertEquals(self.response.status_code, 200)
        

        
