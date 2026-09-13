from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from bots.models import BotStates
from bots.tasks.launch_scheduled_bot_task import launch_scheduled_bot


class TestScheduledBotRedelivery(SimpleTestCase):
    def run_schedule(self, join_at, message_join_at):
        bot = SimpleNamespace(state=BotStates.SCHEDULED, join_at=join_at, object_id="bot_test", project=Mock())
        bot.project.organization.out_of_credits.return_value = False
        with patch("bots.tasks.launch_scheduled_bot_task.Bot.objects.get", return_value=bot), patch("bots.tasks.launch_scheduled_bot_task.launch_bot") as launch, patch("bots.tasks.launch_scheduled_bot_task.BotEventManager.create_event") as event:
            launch_scheduled_bot.run(32, message_join_at.isoformat())
        return launch, event

    def test_expired_queue_message_does_not_launch(self):
        join_at = timezone.now() - timezone.timedelta(hours=12)
        launch, event = self.run_schedule(join_at, join_at)
        launch.assert_not_called()
        event.assert_called_once()

    def test_old_message_after_reschedule_does_not_launch(self):
        launch, event = self.run_schedule(timezone.now() + timezone.timedelta(hours=1), timezone.now())
        launch.assert_not_called()
        event.assert_not_called()

    def test_current_schedule_still_launches(self):
        join_at = timezone.now() + timezone.timedelta(minutes=2)
        launch, event = self.run_schedule(join_at, join_at)
        launch.assert_called_once()
        event.assert_called_once()
