# Deploying to Railway + Vercel

This assumes the MongoDB Atlas cluster from `atlas-credentials.env` is
already created and reachable (Atlas Network Access must allow
connections from anywhere - `0.0.0.0/0` - since Railway's outbound IPs
aren't static; add that under Atlas -> Network Access -> Add IP Address ->
"Allow Access from Anywhere").

**Verification honesty note**: `backend/.env` in this zip is already
wired to the real Atlas connection string, and Django's settings/URL
config load cleanly against it. But the sandbox this was prepared in
can only reach a short allow-list of package-registry domains over
HTTP(S) - it cannot open a raw connection to MongoDB's wire-protocol
port (27017), so the actual read/write round-trip to your cluster,
and running `seed_platform` against it, could not be tested here.
Do that verification yourself as the first step below - it should
work, but "should" isn't "verified."

## 1. Backend -> Railway

1. Push this repo to GitHub (or GitLab) - Railway deploys from a git
   repo, not a zip upload.
2. Railway dashboard -> **New Project** -> **Deploy from GitHub repo** ->
   select the repo. If this is a monorepo (backend/frontend/mobile all
   in one repo, as delivered), set the service's **Root Directory** to
   `backend` under Settings -> Source.
3. Railway will detect `backend/Dockerfile` and `railway.json`
   automatically (explicit `builder: DOCKERFILE` is set, so there's no
   ambiguity even if Railway's auto-detection ever changes).
4. **Add a Redis instance**: Railway dashboard -> **New** -> **Database**
   -> **Add Redis**. Once created, go to your backend service ->
   **Variables** -> **New Variable** -> **Add Reference** -> pick the Redis
   service's `REDIS_URL`. This is the one value you can't copy from the
   `.env` file below, since Railway generates it itself.

   Once linked, Railway's Variables tab shows something like this (the
   `${{...}}` parts are Railway's own live template syntax, resolved
   automatically at deploy time - never type a real password into any
   of these fields yourself):
   ```
   REDISHOST=${{RAILWAY_PRIVATE_DOMAIN}}
   REDISPORT=6379
   REDISUSER=default
   REDISPASSWORD=${{REDIS_PASSWORD}}
   REDIS_URL=redis://${{REDISUSER}}:${{REDIS_PASSWORD}}@${{REDISHOST}}:${{REDISPORT}}
   ```
   Confirm each one shows the blue "reference" icon in Railway's UI, not
   a plain typed value - that icon is what confirms it stays correct
   automatically if the Redis password is ever rotated.
5. **Set the rest of the environment variables** on the backend
   service (Variables tab -> Raw Editor, paste all at once) - copy these
   directly from `backend/.env` in this zip:

   ```
   DEBUG=False
   SECRET_KEY=<the value already in backend/.env>
   ALLOWED_HOSTS=ndc-platform-production.up.railway.app,healthcheck.railway.app,.railway.app
   MONGO_URI=<the Atlas connection string already in backend/.env>
   MONGO_DB_NAME=ndc_platform
   JWT_SECRET=<the value already in backend/.env>
   JWT_ACCESS_TOKEN_TTL_MINUTES=30
   JWT_REFRESH_TOKEN_TTL_DAYS=7
   CORS_ALLOWED_ORIGINS=https://ndc-platform.vercel.app,https://ndc-platform-git-main-desward-technology-s-projects.vercel.app,https://ndc-platform-l2y6a8c6k-desward-technology-s-projects.vercel.app
   BOOTSTRAP_ADMIN_EMAIL=admin@ndc.example
   BOOTSTRAP_ADMIN_PASSWORD=<pick a real password now, not ChangeMe123!>
   ```

   No `localhost`/`127.0.0.1` in either value above - this deployment is
   online-only, so there's no local dev origin to allow through.

   (Leave `ANTHROPIC_API_KEY` and the email/SMS/push variables blank for
   now if you don't have those yet - each one silently no-ops rather
   than breaking anything.)

6. Deploy. Confirm the assigned domain matches
   `ndc-platform-production.up.railway.app` (Settings -> Networking) -
   if Railway ever assigns a different one, update `ALLOWED_HOSTS` above
   to match the real domain exactly.
7. **`CORS_ALLOWED_ORIGINS` is already set above** to the real Vercel
   domains for this project - no placeholder step needed here.
8. **Seed the database** (one-time): Railway dashboard -> your backend
   service -> **Settings** -> look for a one-off/shell command runner (the
   exact UI label has changed across Railway versions - it's sometimes
   under a "Command" or terminal icon), run:
   ```
   python manage.py seed_platform
   ```
   If Railway's UI doesn't expose a shell for your plan tier, install the
   Railway CLI locally instead and run `railway run python manage.py seed_platform`.
9. **Verify**: `curl https://<your-railway-domain>/api/v1/health/` should
   return `200 OK`. If it doesn't, check the deploy logs first - almost
   always either `ALLOWED_HOSTS` missing the Railway domain, or the Redis
   reference variable not actually attached.

## 2. Frontend -> Vercel

1. Vercel dashboard -> **Add New** -> **Project** -> import the same GitHub
   repo. Set **Root Directory** to `frontend`.
2. Framework preset should auto-detect as Next.js.
3. **Environment Variables** -> add:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://<your-railway-domain>/api/v1
   ```
4. Deploy. Vercel assigns a domain like `ndc-platform.vercel.app`.

## 3. Close the loop

Go back to Railway and update the backend's `CORS_ALLOWED_ORIGINS` with
the real Vercel domain:

```
CORS_ALLOWED_ORIGINS=https://ndc-platform.vercel.app
```

Redeploy the backend (Railway redeploys automatically on variable
changes). Then log into the live frontend with `BOOTSTRAP_ADMIN_EMAIL`/
`BOOTSTRAP_ADMIN_PASSWORD` and change the password immediately from
Settings -> Security.

## AI configuration

`AI_MODEL` (optional, defaults to `claude-sonnet-4-6`) controls the
exact Claude model used by every AI feature - Executive AI tools, the
chatbot, and AI-assisted reporting all read this one setting, so it
never needs updating in three places. Change it in Railway's Variables
tab and redeploy, no code change required.

`ANTHROPIC_API_KEY` is still the actual blocker if AI features show
"unavailable" - this setting alone does nothing without a real key set.

**Every Executive AI leadership tool now has a genuine rule-based
fallback** (`apps/executive_ai/fallback.py`) that activates
automatically whenever `ANTHROPIC_API_KEY` is missing or invalid -
Ground Briefing, Official Report, Speech, Draft Broadcast, Summarize
Pending Items, and Meeting Agenda all produce a real, useful,
data-driven result built from actual party data instead of a 503, with
zero external dependency. Every response is honestly labeled
`source: "ai"` or `source: "rule_based"` (shown as a badge in the UI)
so it is never presented as if it came from Claude when it did not.
The moment a real API key is configured, every one of these switches
back to the real AI version automatically - nothing else to change.
The general-purpose chatbot and AI-assisted reporting do not have this
fallback (open-ended chat cannot be meaningfully rule-based), and will
still return "unavailable" without a real key.

Two variables that came up in conversation but were deliberately not
added: `ASR_PROVIDER` has no corresponding feature anywhere in this
codebase (no speech recognition exists), so setting it would do
nothing. `COMMISSION_RATE` doesn't map to anything in the current
finance model - Paystack takes its own fee automatically, and there is
no other "commission" concept here. If either of these is meant to
support a real feature, describe what it should do and it can be built
properly, rather than adding a setting that silently has no effect.

## Ground Intelligence and AI leadership tools access tiers

Two tiers, not one flat permission:

- **Top tier** (`analytics.ground_intelligence`: Flagbearer, National
  Chairman, National General Secretary, Superadmin) - can use Ground
  Intelligence, AI reports, and speech generation for *any* unit in
  the party, and are the only ones who can generate a report with
  reporter names included.
- **Scoped tier** (`hierarchy.manage`: every other real executive -
  Regional Chairman, Constituency Chairman, District Coordinator) -
  gets the same tools, but only for their own unit and its
  descendants. A Regional Chairman cannot reach a region they have no
  authority over.

Assigning a Directive to another executive stays top-tier only - it is
deliberately not scoped, since it is meant for national leadership
directing any executive across the party, not a per-jurisdiction tool.

## A demo account login fails with 401 after a new deploy

This means `python manage.py seed_platform` hasn't actually been
re-run against your real production database since the new code
landed - pushing code and deploying it never creates or updates demo
accounts by itself, the seed command is a separate, explicit step.

Run it (via `railway run python manage.py seed_platform` or Railway's
shell) and read its own output carefully - it now reports exactly how
many roles were newly created versus updated to match the current
code, and separately lists by name any demo account it had to skip
entirely (this only happens if a role_code in the demo account list
doesn't match any real role, which would itself be a bug worth
reporting). If the summary shows the expected counts and no skipped
accounts, every demo account's password has just been reset to
`DemoPass123!` (or your `DEMO_ACCOUNTS_PASSWORD` override) - the login
should work immediately after.

Role permissions are also fully re-synced on every run now, not just
created once - so re-running this command is always safe and always
brings roles and demo accounts back in line with whatever code is
currently deployed, without needing to delete anything first.

## Troubleshooting

### A new deploy doesn't seem to reflect, but a brand new page does

`frontend/vercel.json` now sets explicit cache headers: the actual page
content is `no-cache, no-store, must-revalidate` (always re-checked, never
served stale), while `_next/static/*` (content-hashed build assets, safe
to cache forever) stays aggressively cached. Before this, Vercel's
default caching behavior for the page shell itself could occasionally
let an old version linger.

**This alone won't fix it if the actual cause is your own browser** -
the single most common reason "an update doesn't show up" is a normal
browser tab holding an old cached copy from before. To test whether a
deploy genuinely took effect, use one of these, not a normal reload:
- An incognito/private window, or
- A hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows/Linux)

**To confirm the deploy itself actually happened** (separate from
whether your browser shows it): Vercel dashboard -> Deployments -> the
top entry's commit hash should match what you just pushed
(`git log --oneline -1`). Same check applies to Railway for backend
changes - Deployments tab, confirm the commit hash matches, not just
that *a* deployment exists.

### Deploy fails with `Error: '$PORT' is not a valid port number`

This means gunicorn received the literal text `$PORT` instead of the
real port number. `backend/Dockerfile`'s own `CMD` is written in shell
form specifically so `${PORT:-8000}` gets expanded by a real shell at
container startup - this is correct and should not be changed to JSON
array/exec form. The actual cause is a `startCommand` field in
`backend/railway.json`: when present, it overrides the Dockerfile's
`CMD` entirely, and Railway does not run that override through a shell
the same way Docker does, so any `$PORT` in it is never substituted.

**The fix is to not set `startCommand` in `railway.json` at all** and
let the Dockerfile's own `CMD` run. If `railway.json` ever has a
`startCommand` added back (including one that looks correct, with
`$PORT` in it), that is what will break this exact way again - remove
it rather than trying to fix the syntax of the override itself.

### Login fails with a CORS error in the browser console, backend itself looks healthy

If Railway shows the backend deployment as healthy and Vercel shows the
frontend as deployed, but the browser console shows something like
`has been blocked by CORS policy: Response to preflight request
doesn't pass access control check`, the actual request never reached
your app logic at all - it never even needs to, since a real
credential or bug is not involved here.

This almost always means the `CORS_ALLOWED_ORIGINS` value pasted into
Railway has a typo. The two that have actually happened:
`hhttps://...` (a doubled scheme letter) and a bare domain with no
`https://` prefix at all (`ndc-platform.vercel.app` instead of
`https://ndc-platform.vercel.app`). django-cors-headers does exact
string matching against the browser's real `Origin` header, so either
mistake breaks matching completely with no error at Django startup.

**This is now defended against automatically**: `config/settings.py`
normalizes every origin through `apps/core/cors_utils.normalize_cors_origin`,
which fixes both mistakes before they reach django-cors-headers. If
you still see this error after redeploying with the latest code, the
next thing to check is whether Railway has actually redeployed the
latest commit at all - open the Deployments tab and confirm the commit
hash/message shown matches what you just pushed, not a stale one from
before this fix landed.

As a last resort while debugging, `CORS_ALLOW_ALL_ORIGINS=True` in
Railway's variables bypasses the origin check entirely - useful to
confirm the rest of the stack works, not a setting to leave on for a
real production deployment.

### `seed_platform` crashes with `DuplicateKeyError` on `national_id_number`

A real bug fixed in this codebase, not a configuration issue: earlier
versions used a `sparse: True` unique index on `national_id_number`/
`voter_id_number`, which looks correct but never actually worked -
MongoDB's sparse indexes only exclude documents where the field is
truly *absent*, but MongoEngine writes an explicit `null` for an unset
optional field rather than omitting the key, so a second member with no
national ID on file still collided with the first. Fixed with a
*partial* index instead (an explicit filter expression that genuinely
excludes null values). **If you seeded before this fix landed**, run
this once against your real database to repair the existing index:
```
python manage.py fix_user_indexes
```
Safe to run any time - a no-op if the indexes are already correct.

### Railway: "The executable `npm` could not be found" during Deploy › Create container

This means Railway didn't use `backend/Dockerfile` at all - it fell back
to its Nixpacks auto-builder, which happens when the service's **Root
Directory** is left at the repo root instead of `backend`. From the repo
root, Railway can't see `backend/Dockerfile` or `backend/railway.json`,
so it auto-detects instead and gets confused (this is a monorepo with
both a Python backend and a Node frontend in different folders).

**Fix**: service → **Settings** → **Source** → **Root Directory** →
`backend`. Then **Settings** → **Build** → confirm **Builder** shows
"Dockerfile" (select it explicitly if it still shows Nixpacks after
changing Root Directory - it doesn't always re-detect automatically).
Redeploy.

There's no reliable code-only workaround for this one - a root-level
`railway.json` pointing at `backend/Dockerfile` looks like it would work
but doesn't: Railway's Docker build *context* follows the Root Directory
setting too, not just the Dockerfile's path, so `COPY requirements.txt .`
inside the Dockerfile would still fail to find the file (it lives at
`backend/requirements.txt`, not at the repo root). Root Directory has to
actually be set to `backend` in the dashboard.

### Vercel: deployment shows "Ready" but visiting the URL shows a 404

Same underlying cause, opposite platform: Vercel built from the repo
root instead of `frontend/`, so it never found the Next.js app - it
still produces *a* deployment (hence "Ready"), just not the right one.

**Fix**: project → **Settings** → **General** → **Root Directory** →
`frontend`. Redeploy. While there, confirm **Settings** → **Environment
Variables** has `NEXT_PUBLIC_API_BASE_URL` set to your Railway backend's
real URL.

### Railway: healthcheck still fails, gunicorn logs show no crash or exception at all

If the deploy logs show gunicorn booting cleanly (workers up, "Listening
at...") with no traceback anywhere, but the healthcheck still fails,
suspect a **forced HTTPS redirect loop** rather than an app crash.

`DEBUG=False` turns on `SECURE_SSL_REDIRECT` (see `config/settings.py`),
which is correct for production - but Railway (like all platforms that
terminate TLS at their own edge) forwards plain HTTP internally to your
container. Without `SECURE_PROXY_SSL_HEADER` set, Django's
`request.is_secure()` always returns `False`, so it force-redirects
*every* request - including the platform's own healthcheck probe, which
reads a 301/302 as a failure, not a success. This is already fixed in
`config/settings.py` (both `SECURE_PROXY_SSL_HEADER` and a
`SECURE_REDIRECT_EXEMPT` for the health endpoint specifically, in case a
given platform's internal probe bypasses the public edge proxy
entirely and never carries the forwarded-proto header at all) - if
you're running an older checkout, pull the latest commit.

## Demo login accounts (public, by explicit request)

The login page shows one-click "try a demo account" buttons for every
distinct role defined in `seed_platform.py`, 36 in total, grouped into
four sections: the geographic hierarchy (Superadmin, Flagbearer,
National Chairman down through Ordinary Member), National Secretariat
officers (General Secretary, National Organizer, the appointed
Directors, Internal Auditor, the National Women's/Youth Organizers),
auxiliary structures (TEIN, Zongo Caucus, Professionals Forum, the
Diaspora chapter, Council of Elders, Parliamentary Group, a Functional
Committee), and department heads (Communications at all four levels -
National, Regional, Constituency, Branch, matching the constitution's
named positions at each - Finance, Elections, Membership, Women's
Affairs, IT). **This is a deliberate product
decision, not an oversight**: these buttons are visible to anyone who
visits the site, including on the real production deployment, with
full understanding that this means anyone can assume any of these
identities with zero credentials.

**The Superadmin account is a materially larger exposure than every
other one**, and is called out separately for that reason: it carries
`is_superadmin=True`, which bypasses *every* permission check platform
-wide, not just its own Role's permission list. Every other account is
real too, but each is bounded by its actual Role's actual permission
list and organizational-unit scope - a Regional Chairman demo account
can't touch National-level settings, for instance, and most executive
accounts below the top leadership tier (Flagbearer, National Chairman,
General Secretary) only reach Ground Intelligence and the AI leadership
tools within their own jurisdiction, not party-wide - see "Ground
Intelligence and AI leadership tools access tiers" above.

District Co-ordinator carries the same broad, multi-feature permission
set as the other jurisdiction levels (hierarchy, finance, elections,
membership, messaging), broadened by explicit request from Article 17's
narrower coordination-only reading of the District Co-ordinating
Committee - a deliberate override, not an oversight. If constitutional
fidelity on this specific point matters more than demo consistency for
your deployment, the narrower set is one edit away in `seed_platform.py`'s
`district_coordinator` entry.

What's deliberately *not* done, to keep the blast radius bounded even
given that choice:
- Only one demo account (`demo.superadmin@ndc.example`) carries
  `is_superadmin` - every other one only has the real permissions its
  seeded `Role` grants, same as any actual member with that role.
- The accounts and their shared password are defined in exactly two
  places that must stay in sync: `backend/apps/core/management/commands/seed_platform.py`
  (`_seed_demo_accounts`) and `frontend/src/components/auth/demo-login-buttons.tsx`.
  If you ever change `DEMO_ACCOUNTS_PASSWORD` on the backend, update the
  frontend constant to match, or the buttons will silently fail to log
  in.
- Re-running `python manage.py seed_platform` refreshes the demo
  accounts' passwords back to the configured value even if someone
  changed one - the seed command is idempotent and safe to re-run any
  time you want to reset them.

**If you ever want to turn this off** (e.g. before real members start
using the platform for real party business), the fastest path is
deleting the `<DemoLoginButtons ... />` block from
`frontend/src/app/(auth)/login/page.tsx` and redeploying the frontend -
the accounts themselves can stay dormant in the database with no
practical effect if nobody has their credentials and the buttons are
gone.

## Security notes - please act on these

- **This has now happened four times**, each time the same underlying
  mistake: a real database credential ends up hardcoded as a fallback
  default in a git-tracked file (`config/settings.py` and/or
  `.env.example`) instead of living only in an untracked `.env` /
  the deployment platform's own environment variables. First the
  original Atlas cluster's password, then the replacement cluster's
  password, then a Railway Redis password, then both again together
  in a batch of commits made directly against this repo outside of
  this deployment workflow - each caught and removed after the fact,
  but only after already being committed. **`backend/tests/test_no_hardcoded_secrets.py`**
  scans `settings.py` and `.env.example` for real Atlas-cluster-shaped
  hostnames, the specific credential fragments that have already
  leaked, and any `.env.example` value that looks like a real
  generated secret rather than a placeholder. As of this update,
  **that test also runs automatically on every push via
  `.github/workflows/backend-tests.yml`** - a real GitHub Actions
  check, visible on the commit and on any pull request, not something
  that only helps if a human remembers to run pytest first. If this
  check ever shows red, that is exactly what it is for - fix the
  flagged file before merging, do not skip or delete the test or the
  workflow.
- **Given this is the fourth occurrence, rotate both credentials again**:
  Atlas (Database Access, edit the `ndc` user, Edit Password) and
  Redis (Railway, delete and recreate the Redis service to get a fresh
  password, since Railway does not offer a simple "rotate password"
  button for an existing Redis instance). Update `MONGO_URI` and the
  Redis reference variable in Railway to match afterward.
- **If edits keep landing on this repo from outside this workflow**,
  the GitHub Actions check above is the actual backstop now, but it is
  worth asking whoever else has push access to route `config/settings.py`
  and `.env.example` changes through a review step, since those two
  files are specifically where this exact mistake keeps recurring.
- **Incident, now fixed**: a commit made directly against this repo
  ("Fix CORS for Vercel") briefly hardcoded the real Atlas username and
  password into two git-tracked files - `backend/.env.example` (meant
  to hold only safe placeholder values) and directly into
  `backend/config/settings.py`'s source code as a fallback default. It
  also reverted the `IS_TESTING` safety fix that forces the test suite
  onto a safe in-memory database regardless of what's in `.env`. All
  three are fixed here: both files now hold no real credentials, and
  `IS_TESTING` unconditionally forces `mongomock://localhost` again.
  **Resolved**: rather than just rotating the exposed
  `baristernkuah_db_user` credential on the same cluster, a brand-new
  Atlas cluster and database user were created from scratch
  (`ndc` on `cluster0.xi8wc6t.mongodb.net` - see `backend/.env`),
  fully sidestepping the exposed credential rather than reusing
  anything from it. **The old cluster/user should be deleted in Atlas**
  once the new one is confirmed working, closing this out completely
  rather than leaving a dormant, no-longer-referenced credential
  sitting in Atlas indefinitely.
- **The old Atlas password had also passed through this chat and
  earlier zips before the cluster was replaced.** Moot now that nothing
  in this deployment references that cluster/user any more - but worth
  knowing why a full cluster replacement was the cleaner move here
  rather than just a password rotation on the same one.
- **Never commit `backend/.env` to git.** It already has `.env` in
  `.gitignore`, so a plain `git add .` won't pick it up - but double
  check with `git status` before every push, especially after any
  direct edits made through GitHub's own web interface rather than this
  workflow, since those bypass your local `.gitignore` entirely (the
  file itself isn't the .gitignore's business at that point - a web
  edit to a tracked file is just a normal commit, regardless of what
  your local machine's .gitignore says).
- Change `BOOTSTRAP_ADMIN_PASSWORD` before you actually invite real
  members to use this - `ChangeMe123!` is a placeholder, not a real
  password, and it's now the login for a real database record once
  `seed_platform` runs.
