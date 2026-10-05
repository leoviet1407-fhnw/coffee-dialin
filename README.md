# fristen

A small web app for tracking Swiss admin deadlines — permit renewals, insurance switch windows, tax filing, lease notice periods — in one place, with email reminders and calendar export.

## Why

These deadlines are scattered across letters, portals and half-remembered rules, and missing one is expensive. Existing tools are either generic to-do apps that don't know the rules, or nothing at all.

## Status

Early. Nothing here is stable yet.

## Stack

- Frontend: _TBD_
- Backend: _TBD_
- Database: _TBD_
- Email: _TBD_

## Getting started

```bash
git clone <repo-url>
cd fristen
cp .env.example .env
# install dependencies
# run the dev server
```

The app should then be available at `http://localhost:3000`.

## Environment variables

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | Connection string for the database |
| `EMAIL_API_KEY` | API key for sending reminder emails |
| `APP_URL` | Base URL, used in links inside emails |

## Project structure

```
src/        application code
public/     static assets
docs/       notes and reference material
```

## Roadmap

- [ ] Deadline model and CRUD
- [ ] Seeded set of common Swiss deadlines
- [ ] Email reminders
- [ ] ICS / calendar export
- [ ] Accounts and authentication

## Contributing

Not open to contributions yet.

## License

_TBD_
