# Utilise une image Python minimale
FROM python:3.11-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie les dépendances
COPY requirements.txt .

# Installe les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste du code dans le conteneur
COPY . .

# Rend le script exécutable
RUN chmod +x start.sh

# Démarre le serveur en utilisant la variable d’environnement PORT (Cloud Run)
CMD ["./start.sh"]

