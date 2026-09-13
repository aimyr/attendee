import logging
import os
import signal

from celery import shared_task
from celery.signals import worker_shutting_down
from django.utils import timezone

from bots.bot_controller import BotController
from bots.models import Bot, BotEventManager, BotEventSubTypes, BotEventTypes, BotStates

logger = logging.getLogger(__name__)


@shared_task(bind=True, soft_time_limit=3600)
def run_bot(self, bot_id):
    # Late-acknowledged tasks can be redelivered after a worker restart. A
    # finished bot must be acknowledged without starting another controller.
    try:
        bot = Bot.objects.only("state", "join_at").get(id=bot_id)
    except Bot.DoesNotExist:
        logger.info("Skipping deleted bot %s", bot_id)
        return
    if bot.state in BotStates.post_meeting_states():
        logger.info("Skipping finished bot %s in state %s", bot_id, BotStates.state_to_api_code(bot.state))
        return

    if bot.state == BotStates.STAGED and bot.join_at and bot.join_at < timezone.now() - timezone.timedelta(minutes=5):
        logger.info("Skipping expired staged bot %s", bot_id)
        BotEventManager.create_event(bot=bot, event_type=BotEventTypes.FATAL_ERROR, event_sub_type=BotEventSubTypes.FATAL_ERROR_BOT_NOT_LAUNCHED)
        return

    logger.info(f"Running bot {bot_id}")
    bot_controller = BotController(bot_id)
    bot_controller.run()


def kill_child_processes():
    # Get the process group ID (PGID) of the current process
    pgid = os.getpgid(os.getpid())

    try:
        # Send SIGTERM to all processes in the process group
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass  # Process group may no longer exist


@worker_shutting_down.connect
def shutting_down_handler(sig, how, exitcode, **kwargs):
    # Just adding this code so we can see how to shut down all the tasks
    # when the main process is terminated.
    # It's likely overkill.
    logger.info("Celery worker shutting down, sending SIGTERM to all child processes")
    kill_child_processes()
