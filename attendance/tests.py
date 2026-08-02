"""
Tests for attendance timing.

Late/present is decided from local wall-clock time, so TIME_ZONE is part of the
feature rather than a display preference. It was set to 'Asia/Manila' while the
schools are in Barbados — twelve hours out — so a 07:00 arrival was evaluated
as 19:00 and every punctual student was marked late.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone


def _status_for(moment, cutoff_hour=7, cutoff_minute=10):
	"""Mirror of the decision in attendance/views.py::mark_by_face."""
	local = timezone.localtime(moment)
	late = local.hour > cutoff_hour or (local.hour == cutoff_hour and local.minute >= cutoff_minute)
	return 'late' if late else 'present'


class AttendanceTimeZoneTests(TestCase):
	def test_project_timezone_is_the_schools_timezone(self):
		"""Barbados is UTC-4 year round and observes no daylight saving."""
		self.assertEqual(settings.TIME_ZONE, 'America/Barbados')

	def test_arriving_before_the_cutoff_counts_as_present(self):
		# 06:45 local, comfortably before the 07:10 cutoff.
		moment = datetime(2026, 9, 1, 6, 45, tzinfo=ZoneInfo('America/Barbados'))
		self.assertEqual(_status_for(moment), 'present')

	def test_arriving_after_the_cutoff_counts_as_late(self):
		moment = datetime(2026, 9, 1, 7, 30, tzinfo=ZoneInfo('America/Barbados'))
		self.assertEqual(_status_for(moment), 'late')

	def test_exactly_on_the_cutoff_counts_as_late(self):
		moment = datetime(2026, 9, 1, 7, 10, tzinfo=ZoneInfo('America/Barbados'))
		self.assertEqual(_status_for(moment), 'late')

	def test_a_minute_before_the_cutoff_counts_as_present(self):
		moment = datetime(2026, 9, 1, 7, 9, tzinfo=ZoneInfo('America/Barbados'))
		self.assertEqual(_status_for(moment), 'present')

	@override_settings(TIME_ZONE='Asia/Manila')
	def test_the_original_bug_is_reproducible(self):
		"""Pins why this matters: under the old setting a punctual arrival was late."""
		timezone.deactivate()
		moment = datetime(2026, 9, 1, 6, 45, tzinfo=ZoneInfo('America/Barbados'))
		self.assertEqual(_status_for(moment), 'late')

	def test_a_school_elsewhere_can_override_the_zone(self):
		with override_settings(TIME_ZONE='Europe/London'):
			timezone.deactivate()
			# 06:45 in Barbados is 11:45 in London — late there, and correctly so.
			moment = datetime(2026, 9, 1, 6, 45, tzinfo=ZoneInfo('America/Barbados'))
			self.assertEqual(_status_for(moment), 'late')
