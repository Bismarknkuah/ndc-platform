# NDC Political Party Management System

The complete platform: backend, web frontend, and mobile app in one place.

```
ndc-platform/
├── backend/    Django REST Framework + MongoEngine API (see backend/README.md)
├── frontend/   Next.js 16 admin/dashboard web app (see frontend/README.md)
├── mobile/     Flutter app - Android + iOS from one codebase (see mobile/README.md)
└── docs/       The actual NDC Constitution (reference source of truth)
```

Each project has its own detailed README with setup instructions, an
honest account of what's built vs. what isn't yet, and notes on how
things were verified. This file is just the map.

**Deploying to Railway (backend) + Vercel (frontend)?** See
[`DEPLOYMENT.md`](./DEPLOYMENT.md) - `backend/.env` in this zip is
already wired to a real MongoDB Atlas cluster, with the exact
environment variables to paste into each platform's dashboard.

## The constitution now drives the platform's design

The full 73-page NDC Constitution was read (OCR'd page-by-page - it's a
scanned/vector-graphic PDF with almost no extractable text layer) and
cross-checked against every relevant part of the system. Two real,
concrete corrections came out of that:

1. **Hierarchy realigned to the real 4 official levels** (Article 11):
   `NATIONAL → REGIONAL → CONSTITUENCY → BRANCH`. The platform previously
   had six (two invented levels, Electoral Area and Zone). District
   Co-ordinating Committee (Article 17) is real but is *not* one of the
   four - it's a non-elected coordinating body, now modeled as an
   auxiliary type rather than a 5th rung in the authority chain.
2. **A whole new module built for Articles 46-47**: the Disciplinary
   Committee system. This is genuinely distinct from the general-purpose
   Complaints module - a specific, timed, quasi-judicial process with a
   standing 3-member committee, statutory deadlines (14 days to convene,
   30 days to conclude, 14 days to appeal), a 2/3-majority requirement to
   vary a recommendation, and a precautionary-suspension power (up to 6
   months, renewable once for 5 more) that's genuinely different from
   anything that existed before. See `apps/discipline` (backend, 16
   tests) and `/discipline` (frontend).

Along the way, three auxiliary organizational types were also renamed to
match Article 10's actual "Integral Organs" list exactly
(`PARLIAMENTARY_CAUCUS` → `PARLIAMENTARY_GROUP`, `DIASPORA_CHAPTER` →
`EXTERNAL_BRANCH`), and the seed data was expanded with the appointed
national officer positions and National Committees the full read
surfaced (Directors of International Relations/Research/Administration/
Elections, an Internal Auditor, and the Political/Economic/Social/
Conflict Resolution Committees).

**The constitution itself is included** at `docs/NDC-Constitution.pdf` -
worth keeping alongside this codebase as the actual reference, since
it's now genuinely the source of truth the platform is built against.

One honest caveat: this is a "mini" constitution - real, but possibly
abridged. `PROFESSIONALS_FORUM` is the one auxiliary type in this system
**not directly confirmed** anywhere in its 73 pages (a reasonable guess
at a Congress-created organ, not a citation) - worth re-checking if a
fuller version of the constitution ever becomes available.

## Opening this in VS Code

Open `ndc-platform.code-workspace` (not any single folder) - it's a
multi-root workspace with `backend`/`frontend`/`mobile` as separate
roots, each with its own Python/Node/Dart tooling context.
`.vscode/launch.json` has ready-to-use run/debug configs: **Django:
runserver** (with real breakpoint support via debugpy), **Django: run
tests**, **Next.js: dev server**, a **Backend + Frontend** compound that
starts both together, and two Flutter configs (Android emulator vs.
iOS/desktop, pre-set with the right `NDC_API_BASE_URL` for each). You
still need MongoDB/Redis running separately (`docker compose up mongo
redis` from `backend/`) - VS Code gives you a debugger and one-click
run, not a replacement for the database. Recommended extensions
(Python, Pylance, ESLint, Flutter) are listed in the workspace file and
VS Code will prompt to install them on first open.

## Quick start order

The backend is the foundation everything else talks to - start there.

### 1. Backend

```bash
cd backend
cp .env.example .env   # edit MONGO_URI + ANTHROPIC_API_KEY etc.
docker compose up      # or see backend/README.md for a non-Docker setup
python manage.py seed_platform
```

Runs at `http://localhost:8000`. **364 passing tests**, zero lint
errors. See `backend/README.md` for the full endpoint map: auth,
hierarchy (matching the real constitution), membership, messaging,
elections, finance, donations, welfare, complaints, the new Disciplinary
Committee system, documents, media, volunteers, analytics/GIS,
AI-assisted reporting, the Position Management module's Role CRUD, and
the platform assistant chatbot.

### 2. Frontend (web)

```bash
cd frontend
cp .env.example .env.local   # point at the backend above
npm install
npm run dev      # http://localhost:3000
npm test         # 51 passing unit/component tests
```

Next.js 16 + TypeScript + Tailwind v4, real production build verified
(28 routes). Every module from the original scope is built, the
hierarchy matches Article 11 exactly, and the new `/discipline` module
covers the full Articles 46-47 workflow (report → convene → recommend →
decide → appeal). See `frontend/README.md` for the full phase-by-phase
build history and the one honest verification gap (no headless browser
in the build sandbox, so Playwright e2e specs are written but
unexecuted).

### 3. Mobile (Android + iOS)

```bash
cd mobile
flutter create --platforms=android,ios --org com.ndc .
flutter pub get
flutter run
```

One Dart codebase, zero platform-specific branching. Confirmed no use
of `Platform.isAndroid`/`Platform.isIOS` or platform channels anywhere in
`lib/`, and confirmed to have no hardcoded reference to the old
hierarchy level names either (it treats `unit_type` as a plain string),
so the constitutional realignment needed zero mobile changes. Covers
auth, dashboard, notifications, membership card (real QR), elections/
voting, events/RSVP, volunteer signup, welfare requests, discussion
groups, and direct messaging. The new Disciplinary Committee system and
the chatbot are currently web-only - not yet ported to Flutter. See
`mobile/README.md` for platform-specific setup notes.

## What's real across all three

Every one of these projects was built and verified with actual tooling
in the environment they were produced in, not written from memory and
assumed to work:

- **Backend**: the full pytest suite actually runs and passes (**364**
  tests), `flake8`/`black` actually run clean, the OpenAPI schema
  actually generates with zero errors - all reconfirmed *after* both the
  hierarchy realignment and the new Discipline module, not just before.
- **Frontend**: `next build` actually succeeds with Turbopack (28
  routes), `tsc --noEmit` and `eslint` actually run clean, **51 Vitest
  unit/component tests actually run and pass**. The one honest gap: no
  headless browser was reachable in the sandbox this was built in, so
  Playwright e2e specs are written against the real app but were never
  run.
- **Mobile**: could not run `flutter analyze`/`flutter build` (no
  Flutter SDK in the sandbox), so every file was reviewed by hand and
  checked for brace/paren balance programmatically instead.

Where something couldn't be verified, that's stated plainly in the
relevant README rather than left for you to discover later.

## Frontend build progress

- **Phases 1-10**: foundation, hierarchy/members, departments/Position
  Management, messaging, elections, finance/donations/welfare/
  complaints, events/documents/media, analytics+GIS, settings, polling
  agents + chat
- **Testing & polish pass**: 46 real passing Vitest tests, Playwright
  specs written (unexecuted), Framer Motion applied with restraint, a
  real installable PWA manifest
- **Platform assistant**: a 24/7 chatbot available to every user, safely
  scoped (no database/tool access given to the model)
- **Constitutional realignment**: hierarchy corrected to the real
  4-level chain, District Co-ordinating Committee properly modeled
- **Disciplinary Committee system**: the full Articles 46-47 workflow,
  built end-to-end after reading the rest of the constitution

No known functional gaps remain against the original scope, and the
organizational model now matches the party's actual governing document
rather than an assumption about it - verified section by section, not
just at a glance.
