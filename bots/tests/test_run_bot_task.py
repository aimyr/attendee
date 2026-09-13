from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from bots.models import Bot, BotStates
from bots.tasks.run_bot_task import run_bot


class TestRunBotRedelivery(SimpleTestCase):
    def test_finished_bots_do_not_start_controllers(self):
        for state in (BotStates.FATAL_ERROR, BotStates.ENDED, BotStates.DATA_DELETED):
            with self.subTest(state=state), patch("bots.tasks.run_bot_task.Bot.objects.only") as query, patch("bots.tasks.run_bot_task.BotController") as controller:
                query.return_value.get.return_value = SimpleNamespace(state=state)
                run_bot.run(30)
                controller.assert_not_called()

    def test_deleted_bot_is_acknowledged_without_controller(self):
        with patch("bots.tasks.run_bot_task.Bot.objects.only") as query, patch("bots.tasks.run_bot_task.BotController") as controller:
            query.return_value.get.side_effect = Bot.DoesNotExist
            run_bot.run(30)
            controller.assert_not_called()

    def test_staged_bot_still_starts(self):
        with patch("bots.tasks.run_bot_task.Bot.objects.only") as query, patch("bots.tasks.run_bot_task.BotController") as controller:
            query.return_value.get.return_value = SimpleNamespace(state=BotStates.STAGED, join_at=timezone.now())
            run_bot.run(34)
            controller.assert_called_once_with(34)
            controller.return_value.run.assert_called_once_with()

    def test_expired_staged_bot_does_not_join_old_meeting(self):
        with patch("bots.tasks.run_bot_task.Bot.objects.only") as query, patch("bots.tasks.run_bot_task.BotController") as controller, patch("bots.tasks.run_bot_task.BotEventManager.create_event") as event:
            query.return_value.get.return_value = SimpleNamespace(state=BotStates.STAGED, join_at=timezone.now() - timezone.timedelta(hours=12))
            run_bot.run(32)
            controller.assert_not_called()
            event.assert_called_once()
