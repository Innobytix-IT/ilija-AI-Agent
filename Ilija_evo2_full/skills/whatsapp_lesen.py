"""
Skill zum Lesen der letzten eingehenden WhatsApp Nachricht.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def whatsapp_lesen(kontakt_name: str):
    # Zugriff auf den globalen Driver
    import browser_oeffnen
    driver = browser_oeffnen.driver

    if driver is None:
        return "❌ Fehler: Browser ist nicht offen."

    try:
        # 1. Kontakt suchen und anklicken (wie beim Senden)
        search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        search_box.click()
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.BACKSPACE)
        search_box.send_keys(kontakt_name)
        time.sleep(2)
        search_box.send_keys(Keys.ENTER)
        time.sleep(1)

        # 2. Die letzte EINGEHENDE Nachricht finden
        # Wir suchen nach div-Containern, die die Klasse für eingehende Nachrichten haben
        messages = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in")]')
        
        if not messages:
            return f"Keine eingehenden Nachrichten von {kontakt_name} gefunden."

        # Die letzte Nachricht in der Liste nehmen
        last_msg = messages[-1].text
        
        # Säubern (WhatsApp Texte enthalten oft Zeitstempel am Ende)
        clean_msg = last_msg.split('\n')[0] 
        
        return f"Letzte Nachricht von {kontakt_name}: '{clean_msg}'"
    except Exception as e:
        return f"❌ Fehler beim Lesen: {str(e)}"

AVAILABLE_SKILLS = [whatsapp_lesen]
