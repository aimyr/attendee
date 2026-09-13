from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

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
            query.return_value.get.return_value = SimpleNamespace(state=BotStates.STAGED)
            run_bot.run(34)
            controller.assert_called_once_with(34)
            controller.return_value.run.assert_called_once_with()
