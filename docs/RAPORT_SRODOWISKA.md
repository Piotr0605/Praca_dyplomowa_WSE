# Raport: kontrola środowiska (tydzień 1, poniedziałek 2.11.2026)

**System:** macOS 26.6.2, Apple Silicon (arm64), 107 GB wolnego miejsca na dysku.

## Stan po konfiguracji

| Narzędzie | Stan | Wersja / uwagi |
|---|---|---|
| Git | ✅ | 2.50.1, remote `origin` → github.com/Piotr0605/Praca_dyplomowa_WSE |
| Docker Desktop | ✅ | Docker 29.5.3, silnik działa (`hello-world` uruchomiony), 10 CPU, ~8 GB RAM dla Dockera |
| Docker Compose | ✅ | v5.1.4 |
| Python | ✅ | **3.13.13** (zarządzany przez `uv` 0.11.19). Systemowy `python3` to 3.9.6 i nie jest używany w projekcie |
| Środowisko wirtualne backendu | ✅ | `backend/.venv` (Python 3.13), wersja zapisana w `backend/.python-version` |
| Node.js LTS + npm | ✅ | Node v26.13.0, npm 11.20.0, zainstalowane w `~/.local/share/node` (bez uprawnień administratora, suma SHA-256 zweryfikowana) |
| VS Code + polecenie `code` | ✅ | `code` podlinkowane w `~/.local/bin` |
| Rozszerzenia VS Code | ✅ | Python, Pylance, Ruff, ESLint, Tailwind CSS IntelliSense, Docker |
| Porty 5432 / 8000 / 5173 | ✅ | wolne |
| Plik `.env` | ✅ | z `.env.example`, losowe hasło bazy i klucz JWT (`openssl rand`), uprawnienia 600, ignorowany przez Git |

## Decyzja do pracy dyplomowej
Wersja Pythona w projekcie: **3.13**, lokalnie i w obrazie Dockera backendu (`python:3.13-slim`).
Ta sama wersja w obu miejscach eliminuje różnice typu „u mnie działa”.
