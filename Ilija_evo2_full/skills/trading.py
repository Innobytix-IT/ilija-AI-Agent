import time
import random

# Globale Variablen simulieren den Session-Status im Speicher
# In einer echten App würden wir das sicherer speichern.
SESSION_DATA = {
    "logged_in": False,
    "user": None,
    "balance_usd": 10000.0  # Startguthaben
}

def trading_login(plattform: str, api_key: str):
    """
    Loggt den User in eine Börse ein (z.B. Binance, Kraken).
    Benötigt für alle weiteren Aktionen.
    """
    time.sleep(1) # Simuliere Netzwerk-Latenz
    
    # Hier würde der echte API-Check stattfinden
    if plattform.lower() in ["binance", "kraken", "coinbase"]:
        SESSION_DATA["logged_in"] = True
        SESSION_DATA["user"] = "IlijaMaster"
        return f"✅ Login erfolgreich bei {plattform}. Guthaben: {SESSION_DATA['balance_usd']} USD."
    else:
        return f"❌ Fehler: Plattform '{plattform}' wird nicht unterstützt."

def markt_check(symbol: str):
    """
    Prüft den aktuellen Kurs und Nachrichten für ein Symbol (z.B. BTC, ETH).
    Gibt Preis und eine Tendenz zurück.
    """
    if not SESSION_DATA["logged_in"]:
        return "⚠️ Fehler: Du bist nicht eingeloggt. Bitte nutze erst 'trading_login'."

    sym = symbol.upper()
    # Wir simulieren Preise
    preis = random.uniform(30000, 65000) if sym == "BTC" else random.uniform(1500, 3500)
    
    # Einfache simulierte Analyse
    tendenz = random.choice(["KAUFEN", "VERKAUFEN", "HALTEN"])
    nachricht = random.choice([
        "Regulierung positiv", "Inflation sinkt", "Großer Investor verkauft", "Netzwerk-Update erfolgreich"
    ])
    
    return f"📊 {sym}-Analyse:\nPreis: {preis:.2f} USD\nNews: {nachricht}\nEmpfehlung: {tendenz}"

def trade_ausfuehren(aktion: str, symbol: str, betrag: float):
    """
    Führt einen Kauf oder Verkauf aus.
    aktion: 'buy' oder 'sell'
    symbol: 'BTC', 'ETH'
    betrag: Menge in USD
    """
    if not SESSION_DATA["logged_in"]:
        return "⚠️ Fehler: Zugriff verweigert. Bitte einloggen."

    if betrag > SESSION_DATA["balance_usd"] and aktion.lower() == "buy":
        return f"❌ Fehler: Nicht genug Guthaben ({SESSION_DATA['balance_usd']} USD)."

    # Trade simulieren
    neuer_saldo = SESSION_DATA["balance_usd"] - betrag if aktion.lower() == "buy" else SESSION_DATA["balance_usd"] + betrag
    SESSION_DATA["balance_usd"] = neuer_saldo
    
    transaktions_id = random.randint(1000000, 9999999)
    return f"🚀 ORDER AUSGEFÜHRT: {aktion.upper()} {betrag} USD in {symbol.upper()}.\nID: #{transaktions_id}. Neuer Saldo: {neuer_saldo:.2f} USD."

# Die Liste der Skills, die Ilija sieht
AVAILABLE_SKILLS = [trading_login, markt_check, trade_ausfuehren]
