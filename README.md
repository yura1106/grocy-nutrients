# Grocy Nutrients

*Nutrition tracking and consumption analytics for Grocy.*

Turn your self-hosted [Grocy](https://grocy.info) instance into a daily nutrition tracker — log what you actually ate, set per-day calorie / protein / fat / carb targets, and analyze recipe nutrient breakdowns and consumption history over time. An optional household mode lets multiple people share a single Grocy account, each with their own goals and credentials.

*FastAPI + Vue 3. Per-user Grocy API keys are encrypted at rest with [Themis SCellSeal](https://docs.cossacklabs.com/themis/crypto-theory/cryptosystems/secure-cell/), keyed by the user's bcrypt hash — so the database alone doesn't reveal them.*

![Today's nutrient intake against per-day targets](docs/screenshots/hero.png)

---

## Features

### Daily nutrition tracking

Set per-day calorie / protein / fat / carb / sugar targets and see today's intake against them in real time. Each user has their own goals — useful when household members have different dietary needs.

![Daily nutrition limits — configuring targets](docs/screenshots/daily-nutrition.png)

### Recipe nutrient analysis

Compute the nutrient breakdown for any recipe by aggregating its ingredient quantities, then see the result per portion. Useful for planning meals around your daily targets.

![Recipe nutrient breakdown per portion](docs/screenshots/recipe-nutrients.png)

### Consumption logging & history

Quickly log what you ate from your stocked products, browse the full consumption history with filters, and bulk-import past data from the Grocy stock log.

![Consumption history view](docs/screenshots/consumption-history.png)

### Product analytics

See which products you actually use over time — frequency, totals, category breakdowns — to inform purchase planning and reduce waste.

![Consumed products stats](docs/screenshots/product-stats.png)

### Multi-user household mode

A single Grocy instance can be shared across household members, each with their own login, encrypted API key, and individual nutrition goals — without exposing the Grocy admin API key to anyone.

### Auth & account management

Email-based registration, JWT auth with refresh tokens, password reset over SMTP, and self-service account deletion.

---

## Architecture highlights

### Per-user encrypted Grocy API keys

Each user's Grocy API key is stored encrypted at rest with [Themis SCellSeal](https://docs.cossacklabs.com/themis/crypto-theory/cryptosystems/secure-cell/), using the user's own bcrypt password hash as the encryption key. There is no global master key in the system — a database leak alone doesn't expose any API keys, since the attacker would still need each user's password hash. When a user changes their password, all of that user's API keys are transparently re-encrypted under the new hash.

### Household-aware FastAPI dependency

Grocy API keys are stored per-`(user, household)` pair in the `HouseholdUser` join table. A single FastAPI dependency, `get_grocy_api`, validates active membership in the requested household, decrypts the user's API key for that household, and returns a configured Grocy client — so route handlers stay free of authz and crypto details:

```python
@router.get("/products")
async def list_products(grocy: GrocyAPI = Depends(get_grocy_api)):
    return await grocy.get_products()
```

### Background sync via Celery + Redis

Products and recipes are pulled from Grocy daily at 04:00 by a Celery beat job and cached locally in PostgreSQL, so chart-heavy views (consumption stats, recipe nutrient breakdowns) stay snappy without hammering the upstream Grocy API on every request. The same worker handles range-checked nutrition-limit notifications over email.

---

## Tech stack

**Backend:** FastAPI · SQLModel · PostgreSQL · Redis · Celery · Themis · Alembic
**Frontend:** Vue 3 · TypeScript · Pinia · Vue Router · Tailwind CSS · Vite
**Infra:** Docker Compose · GitHub Actions

---

<details>
<summary><strong>Run it locally</strong></summary>

**Prerequisites:** Docker and Docker Compose.

```bash
git clone https://github.com/yura1106/grocy-nutrients.git
cd grocy-nutrients
cp .env.backend.example .env.backend
# Edit .env.backend — at minimum set JWT_SECRET_KEY.
# To enable password reset emails, fill in the SMTP_* variables.
make up
```

Open the app:
- Frontend: http://localhost:8888
- API docs (Swagger): http://localhost:8888/api/docs

After registering, create a household and enter your Grocy URL and API key in the form. If your Grocy instance runs on a private network (e.g. `192.168.x.x`), set `ALLOW_PRIVATE_GROCY_URL=True` in `.env.backend`.

Common make targets: `make migrate`, `make lint-python`, `make lint-js`, `make ci`.

</details>

---

## Roadmap

- [ ] Meal plan management — schedule meals ahead, see projected nutrient intake against targets
- [ ] Backend refactoring pass — service-layer cleanup, unified error handling
- [ ] Recipe nutrient algorithm deep-dive doc (replacing the outdated `RECIPE_NUTRIENTS.md`)

---

## License

[MIT](./LICENSE)

## Author

Built by **Yurii Kuznietsov** — [GitHub](https://github.com/yura1106) · [LinkedIn](https://www.linkedin.com/in/yurakuznetsov1106/)

---

*Grocy Nutrients is an independent companion project and is not affiliated with the [Grocy](https://grocy.info) project.*
