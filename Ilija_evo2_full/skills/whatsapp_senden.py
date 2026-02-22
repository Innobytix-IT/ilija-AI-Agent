from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import sys
import os

# WICHTIG: Zugriff auf den Driver aus dem anderen Modul
try:
    from browser_oeffnen import driver
except ImportError:
    driver = None

def whatsapp_senden(kontakt_name: str, nachricht: str):
    global driver
    # Falls der Import oben nicht geklappt hat, suchen wir im Speicher
    if driver is None:
        import browser_oeffnen
        driver = browser_oeffnen.driver

    if driver is None:
        return "❌ Fehler: Kein aktiver Browser gefunden. Bitte 'browser_oeffnen' zuerst ausführen."

    try:
        # 1. Kontakt suchen (Wir nutzen das Suchfeld oben links für mehr Stabilität)
        search_box_xpath = '//div[@contenteditable="true"][@data-tab="3"]'
        search_box = driver.find_element(By.XPATH, search_box_xpath)
        search_box.click()
        search_box.send_keys(Keys.CONTROL + "a") # Alten Text löschen
        search_box.send_keys(Keys.BACKSPACE)
        search_box.send_keys(kontakt_name)
        time.sleep(2) # Warten auf Suchergebnisse
        search_box.send_keys(Keys.ENTER)
        time.sleep(1)

        # 2. Nachricht schreiben
        msg_box_xpath = '//div[@contenteditable="true"][@role="textbox"][@data-tab="10"]'
        msg_box = driver.find_element(By.XPATH, msg_box_xpath)
        msg_box.send_keys(nachricht)
        time.sleep(0.5)
        msg_box.send_keys(Keys.ENTER)

        return f"✅ Nachricht an '{kontakt_name}' wurde erfolgreich gesendet."
    except Exception as e:
        return f"❌ Fehler beim Senden: {str(e)}"

AVAILABLE_SKILLS = [whatsapp_senden]
