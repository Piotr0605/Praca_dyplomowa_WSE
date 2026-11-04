# Obraz frontendu w trybie deweloperskim (serwer Vite). Wersja produkcyjna: etap 9 (nginx).
FROM node:26-slim

WORKDIR /app
RUN chown node:node /app

# Aplikacja nie działa jako root (dobra praktyka bezpieczeństwa kontenerów).
USER node

# Najpierw same zależności: warstwa obrazu przebudowuje się tylko po zmianie package*.json.
# `npm ci` instaluje dokładnie wersje z package-lock.json.
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci --no-fund --no-audit

COPY --chown=node:node . .

EXPOSE 5173

# --host: serwer musi nasłuchiwać na wszystkich interfejsach kontenera, inaczej port
# przekazany przez Dockera nie będzie osiągalny z przeglądarki.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
