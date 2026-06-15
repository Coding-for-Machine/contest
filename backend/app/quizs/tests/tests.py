# app/quizs/tests/tests.py
from django.test import TestCase
from ninja.testing import TestClient
from quizs.models import Test
from quizs.api import router

from datetime import datetime, timedelta

class TestTests(TestCase):
    def setUp(self):
        self.now = datetime.now()
        self.test_obj = Test.objects.create(
            title="Matematika Test!",
            slug="matematika-test",
            duration_minutes=60,
            question_count=10,
            min_pass_percentage=65,
            is_active=True,
            start_time=self.now,
            end_time=self.now + timedelta(days=1),
        )
        print("ok")
    def get_tests_list(self):
        test = Test.objects.get(is_active=True, title="Matematika Test!")
        self.assertEqual(test.title, "Matematika Test!", "ok")