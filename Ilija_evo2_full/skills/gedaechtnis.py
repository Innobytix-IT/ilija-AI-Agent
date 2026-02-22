import chromadb
from chromadb.utils import embedding_functions
import uuid
import os

# Konfiguration
DB_PATH = "./memory/ilija_db"
EF = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
CLIENT = chromadb.PersistentClient(path=DB_PATH)

# WIR NUTZEN NUR NOCH EINE SAMMLUNG FÜR ALLES
COLLECTION_NAME = "globales_wissen"

def wissen_speichern(text: str):
    """
    Speichert eine wichtige Information im Langzeitgedächtnis.
    """
    try:
        col = CLIENT.get_or_create_collection(name=COLLECTION_NAME, embedding_function=EF)
        
        doc_id = str(uuid.uuid4())
        col.add(
            documents=[text],
            metadatas=[{"type": "memory", "timestamp": str(os.path.getmtime(__file__))}], # Dummy Metadata
            ids=[doc_id]
        )
        return f"✅ Info gespeichert: '{text}'"
    except Exception as e:
        return f"❌ Speicherfehler: {e}"

def wissen_abrufen(suchbegriff: str):
    """
    Durchsucht das gesamte Gedächtnis nach dem Begriff.
    """
    print(f"🧠 KERNEL: Durchsuche 'One-Brain' nach '{suchbegriff}'...")
    
    try:
        col = CLIENT.get_or_create_collection(name=COLLECTION_NAME, embedding_function=EF)
        
        # Wir holen uns die Top 3 Treffer
        results = col.query(query_texts=[suchbegriff], n_results=3)
        
        gefunden = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                dist = results['distances'][0][i]
                
                # Debug-Ausgabe für dich im Terminal
                print(f"   -> Gefunden: '{doc}' (Distanz: {dist:.4f})")
                
                # Distanz < 1.6 ist meistens ein guter Treffer. 
                # Wir sind jetzt etwas toleranter.
                if dist < 1.8: 
                    gefunden.append(doc)
        
        if not gefunden:
            return "Nichts passendes im Gedächtnis gefunden."
            
        return "Gefundene Infos:\n" + "\n".join(gefunden)

    except Exception as e:
        return f"Suchfehler: {e}"

# Debug-Funktion für dich (nicht für die KI)
def zeige_alles():
    try:
        col = CLIENT.get_collection(name=COLLECTION_NAME, embedding_function=EF)
        return col.get()
    except:
        return "Leer."

AVAILABLE_SKILLS = [wissen_speichern, wissen_abrufen]
