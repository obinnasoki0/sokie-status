# Sokie status

External uptime monitor for [Sokie](https://mysokie.com). Every 5 minutes a GitHub Actions run checks:

- the customer & runner app (mysokie.com)
- the admin portal
- the backend health endpoint (database, scheduled jobs, AI security monitor)
- the sign-in service

If anything is still down after a retry, an **outage** issue opens here (GitHub emails the owner) and gets a comment on each failed check; it closes itself when everything recovers.

Runs outside Supabase on purpose, so it still alerts when the backend itself is down. Run it by hand from **Actions → Uptime → Run workflow**.
