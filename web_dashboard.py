from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def read_dashboard():
    if not os.path.exists("trading.log"):
        return "<h2>Aucune activité de trading pour l'instant.</h2>"

    with open("trading.log", "r") as file:
        lines = file.readlines()

    html = """
    <html>
        <head>
            <title>Trading Bot Dashboard</title>
            <style>
                body { font-family: Arial; padding: 20px; background-color: #f7f7f7; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; }
                th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
                tr:hover { background-color: #f1f1f1; }
                code { background-color: #eee; padding: 2px 4px; border-radius: 4px; }
            </style>
        </head>
        <body>
            <h1>🧾 Historique des décisions de trading</h1>
            <table>
                <tr><th>Timestamp</th><th>Entrée</th><th>Décision</th></tr>
    """

    for line in reversed(lines):
        if "INPUT=" in line and "-> DECISION=" in line:
            parts = line.strip().split("] ")
            timestamp = parts[0].replace("[", "")
            input_part, decision_part = parts[1].split(" -> DECISION=")
            html += f"<tr><td>{timestamp}</td><td><code>{input_part}</code></td><td><strong>{decision_part}</strong></td></tr>"

    html += """
            </table>
        </body>
    </html>
    """
    return html
