# app-backend

## Environment variables and hosting notes

- This project expects secrets and API keys to be provided via environment variables. See `.env.example` for the names used.
- When deploying to Render (or similar hosts), set the variables in the service's environment configuration (do NOT commit `.env` or `.env.local` to source control).
- Locally you can copy `.env.example` to `.env` and fill values for development. The application uses `pydantic` settings to read from the environment.

Required variables (examples):

- `GOOGLE_API_KEY` — API key for Google GenAI (if used)
- `REPLICATE_API_TOKEN` — Replicate access token (if used)
- `LAB11_API_KEY` — other LLM provider key (if used)

If you want, I can also create a small startup check that logs missing critical env variables on boot.