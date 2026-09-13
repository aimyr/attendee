import os
from pathlib import Path

from django.test.testcases import SimpleTestCase, TransactionTestCase, override_settings
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from bots.google_meet_bot_adapter.google_meet_bot_adapter import GoogleMeetBotAdapter


@override_settings(MONITOR_DOMAIN_ALLOWLIST_IN_CHROME=True, ENFORCE_DOMAIN_ALLOWLIST_IN_CHROME=False)
class TestGoogleMeetLoginChromeStartup(SimpleTestCase):
    def test_login_with_bidi_can_create_session(self):
        # Exercise the default login/monitoring configuration against real Chrome.
        # Chrome 134 fails during session creation when --guest and BiDi coexist.
        if os.environ.get("DISPLAY") is None:
            display = Display(visible=0, size=(1920, 1080))
            display.start()
            self.addCleanup(display.stop)

        adapter = GoogleMeetBotAdapter.__new__(GoogleMeetBotAdapter)
        adapter.google_meet_bot_login_should_be_used = True
        policy_file = Path("/tmp/attendee-chrome-policies.json")
        previous_policy = policy_file.read_text() if policy_file.exists() else None
        if previous_policy is None:
            self.addCleanup(lambda: policy_file.unlink(missing_ok=True))
        else:
            self.addCleanup(policy_file.write_text, previous_policy)
        adapter.write_chrome_policies_file()

        options = webdriver.ChromeOptions()
        for argument in ("--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"):
            options.add_argument(argument)
        options.set_capability("webSocketUrl", True)
        adapter.add_subclass_specific_chrome_options(options)

        driver = webdriver.Chrome(options=options, service=Service(executable_path="/usr/local/bin/chromedriver"))
        self.addCleanup(driver.quit)
        driver.get("data:text/html,<title>Google Meet Chrome startup</title>")
        self.assertEqual(driver.title, "Google Meet Chrome startup")
        self.assertTrue(driver.capabilities.get("webSocketUrl"))


class TestChromeDriver(TransactionTestCase):
    def test_can_open_google(self):
        # Create virtual display if no real display is available
        if os.environ.get("DISPLAY") is None:
            display = Display(visible=0, size=(1920, 1080))
            display.start()

        try:
            # Set up Chrome options
            options = webdriver.ChromeOptions()
            options.add_argument("--use-fake-ui-for-media-stream")
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-application-cache")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=options, service=Service(executable_path="/usr/local/bin/chromedriver"))

            try:
                # Load Google
                driver.get("https://www.google.com")

                # Verify we can find the Google search box
                search_box = driver.find_element("name", "q")

                # Basic assertion that we found the search box
                self.assertIsNotNone(search_box)

            finally:
                # Clean up driver
                driver.quit()

        except Exception as e:
            self.fail(f"Failed to open Chrome and load Google: {str(e)}")
