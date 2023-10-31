from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from configparser import SectionProxy

from common import countdown, load_html, tmp_path

class BrowserType:
    FIREFOX = 'firefox'
    CHROME = 'chrome'

driver_path = 'driver_path'
use_browser = 'use_browser'
browser_profile_path = 'browser_profile_path'

def source_file(index: str|int):
    return tmp_path / f'source_{index}'

class BrowserControl:
    def __init__(self, config_section: SectionProxy):
        browser_used = config_section[use_browser]
        profile_path = config_section[browser_profile_path]
        if browser_used == BrowserType.FIREFOX:
            from selenium.webdriver import Firefox as Browser
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service
            options = Options()
            options.add_argument('-profile')
            options.add_argument(profile_path)
        elif browser_used == BrowserType.CHROME:
            from selenium.webdriver import Chrome as Browser
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument(f'user-data-dir={profile_path}')
        else:
            raise ValueError(f'')
        service = Service(config_section[driver_path])
        self.browser = Browser(service=service, options=options)
        countdown(2)

    def navigate(self, URL: str):
        self.browser.get(URL)
        countdown(5, True)

    def get_source(self, delete_comment: bool = True) -> str:
        if delete_comment:
            return self.browser.page_source.replace('<!---->', '')
        else:
            return self.browser.page_source

    def find_and_click_button(self, property_name: str, property_value: str) -> bool:
        elems = self.browser.find_elements(By.TAG_NAME, 'button')
        for elem in elems:
            if elem.get_attribute(property_name) == property_value:
                elem.click()
                countdown(5)
                return True
        return False

    def scroll_list(self, class_name: str):
        try:
            elem = self.browser.find_element(By.CLASS_NAME, class_name)
            elem.send_keys(Keys.PAGE_DOWN)
        except Exception as e:
            print(f'Scroll raised an exception of length {len(str(e))}, a few positions only?')

class BrowserControl_Mock(BrowserControl):
    def __init__(self):
        pass

    def find_and_click_button(self, property_name: str, property_value: str) -> bool:
        return False

    def navigate(self, URL: str):
        pass

    def get_source(self) -> str:
        return load_html(tmp_path / 'test.html')

    def scroll_list(self, class_name: str):
        pass
