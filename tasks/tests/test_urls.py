from django.test import TestCase
from django.urls import resolve

from tasks.views import TaskViewSet


class TestUrls(TestCase):

    def test_tasks_urls(self):
        url = "/tasks/"
        self.assertEqual(resolve(url).func.cls, TaskViewSet)  # bcz viewset
