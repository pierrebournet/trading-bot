import subprocess

def start_bot():
    try:
        # Remplace par le bon chemin ou commande de ton bot si besoin
        subprocess.Popen(["python", "main.py"])
        return {"status": "✅ Bot lancé avec succès"}
    except Exception as e:
        return {"status": "❌ Erreur", "details": str(e)}

def stop_bot():
    # Tu peux intégrer une vraie logique d'arrêt si nécessaire (pid, nom process, etc.)
    return {"status": "🛑 Fonction stop à implémenter"}
