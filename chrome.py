from contextlib import contextmanager
from typing import Generator

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


@contextmanager
def driver() -> Generator[webdriver.Chrome, None, None]:
    chrome_options = webdriver.ChromeOptions()

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=chrome_options)

    yield driver

    driver.close()
