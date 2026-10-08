https://minimebook.vercel.app/

## Team to-do (live shared list)

`todo.html` is a shared to-do, workload view and timeline. It also edits the master timeline dates that `roadmap.html` shows, so both pages always agree.

- No login. Anyone with the site link can read and edit, on purpose, so the team can fix each other's work.
- Data lives in a hosted Redis through `api/todo.js` (a Vercel serverless function, no npm packages).
- Changes show up for everyone within a few seconds. Offline edits are kept on the device and sync when back online.
- Safety: deletes go to a trash, the server keeps a snapshot of the whole list for every day for 35 days, and Settings has a download/restore backup.

One-time setup (about 2 minutes):

1. Vercel dashboard, your project, **Storage**, **Create Database**, pick **Upstash for Redis** (Marketplace), connect it to this project (all environments).
2. That adds the `KV_REST_API_URL` and `KV_REST_API_TOKEN` environment variables automatically.
3. Redeploy the project once. Open `todo.html`: the pill at the top should say **Live**. The first visit loads the starter data from `data/todo.json`.

Until the database is connected, the page still works but only on the one device, and says so in the pill.

Master timeline items live in `data/master-timeline.js`. Edit that file to add or rename items.
