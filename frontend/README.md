# NDC Party Platform — Frontend (Complete: Phases 1-10, plus testing, polish, platform assistant & Disciplinary Committee system)

Next.js 16 (App Router, Turbopack) frontend for the [`ndc-backend`](../ndc-backend)
Django REST API. Every request goes to real, verified backend endpoints —
see the API map built via live introspection of the actual Django URL
resolver (not written from memory) earlier in this project's history.

## What's built in Phase 1

- **Project foundation**: Next.js 16 + TypeScript + Tailwind v4, real
  production build verified with Turbopack (`npm run build` succeeds,
  zero TypeScript errors, zero ESLint errors).
- **Brand**: the real NDC umbrella logo (background-removed to a clean
  transparent PNG via ImageMagick flood-fill, verified by compositing
  onto a colored background before use) - used at full visibility as the
  actual brand mark (sidebar header, login card, loading splash) and as
  a large, deliberately faint watermark (5-7% opacity) behind the login
  screen only, per instruction that it stay in the background, not
  compete with the form.
- **Design system**: NDC-specific token set (not a generic shadcn
  default) — see `src/app/globals.css`. Self-hosted fonts via
  `@fontsource` (Sora/Inter/JetBrains Mono) rather than `next/font/google`,
  since Google Fonts' CDN isn't reachable from every deployment network —
  self-hosting also means zero external font requests in production.
- **UI primitives**: hand-authored shadcn/ui-pattern components (Radix
  primitives + CVA + Tailwind) in `src/components/ui/` — the shadcn CLI
  registry (`ui.shadcn.com`) wasn't reachable from the sandbox this was
  built in, so these were authored directly using the same underlying
  libraries the CLI would have generated from.
- **API layer**: Axios client with JWT bearer auth, and correct handling
  of the backend's **rotating** refresh tokens (both access *and* refresh
  are replaced on every refresh call — a subtlety worth flagging since
  it's easy to only persist the new access token and silently break
  after the first refresh). Concurrent 401s share a single in-flight
  refresh rather than racing each other against the single-use refresh
  token. See `src/lib/api/client.ts`.
- **State**: Zustand for auth/locale/command-palette UI state (persisted
  where it should be, not persisted where it shouldn't), TanStack Query
  for all server state.
- **Core layout**: sidebar (permission-aware — items only render if the
  signed-in user's role actually carries the required permission tag,
  mirroring the backend's own ancestor-scoped model), top nav, page
  breadcrumbs, command palette (⌘K/Ctrl+K, real navigation + real member
  search), notification bell (real polling against the notifications
  API), user menu, theme switcher (light/dark/system), language switcher.
- **The signature element**: `OrgUnitPath` — a connected-pill breadcrumb
  for the party's actual constitutional hierarchy (National › Regional ›
  Constituency › Branch, per Article 11 of the actual NDC Constitution),
  distinct from the page
  breadcrumb. This becomes the primary "where am I in the org tree"
  device reused across hierarchy, members, elections, and finance screens
  in later phases.
- **Auth flow**: login (React Hook Form + Zod), session restore on reload
  (verifies the token against `GET /auth/me/` rather than trusting
  persisted state blindly), logout (revokes the refresh token
  server-side).
- **Dashboard**: fully wired to the real `GET /api/v1/dashboard/`
  endpoint, rendering exactly the sections the backend actually returns
  for that user's role (teams led, upcoming meetings, pending tasks,
  active elections, upcoming events, recent broadcasts, finance summary
  with a real Recharts breakdown) — no client-side role branching, same
  principle the backend endpoint itself uses.
- **System UI states**: loading skeletons, empty states, error states
  (with retry), 403 (reusable `ForbiddenState` + static route), 404,
  500 (`error.tsx` + `global-error.tsx` for root-layout failures),
  offline banner (real `navigator.onLine` + online/offline events via
  `useSyncExternalStore`).
- **i18n**: a real, working mechanism (Zustand-persisted locale +
  dictionary lookup with English fallback for un-translated keys) rather
  than a placeholder switcher — but honestly scoped: only Phase 1's
  chrome strings (nav labels, auth form, common actions) are translated
  into Twi and Eʋegbe so far. Strings get localized phase-by-phase as
  each page is built, not translated ahead of content that doesn't exist
  yet.

## What's built in Phase 2: Hierarchy & Members

- **Hierarchy browser** (`/hierarchy`): search/filter across all 20 real
  unit types (the 6-level main chain, TEIN's own 6-level chain, and 8
  auxiliary types — not a simplified subset), unit detail pages with
  ancestor path, child-unit list, create-child, and deactivate (soft
  delete, blocked server-side if the unit still has active children —
  the UI surfaces that constraint rather than hiding it).
- **Member directory** (`/members`): searchable/paginated table (name,
  email, membership ID), status filter, member detail pages with full
  profile, **suspend/reactivate** and **transfer** actions wired to the
  real endpoints confirmed in the last session (`PATCH
  /auth/members/<id>/`, `POST /auth/members/<id>/transfer/`), and a
  **Provision Member** form covering the complete
  `AdminCreateMemberSerializer` field set (Ghana Card number, voter ID,
  emergency contact, etc.) — shows the one-time temporary password
  exactly once, with copy-to-clipboard, matching the backend's own
  "shown once" security model.
- **`UnitPicker`**: a reusable searchable combobox for choosing an
  organizational unit (used in provisioning, transfer, and unit
  creation), optionally constrained to a specific `unit_type` — e.g. the
  create-unit dialog automatically restricts the parent picker to
  whatever type the backend's `expected_parent_type()` rule requires for
  the selected unit type, mirrored exactly from
  `apps.hierarchy.constants` on the backend.
- **`DataTable`**: a reusable TanStack Table wrapper (loading state,
  empty state, row click) - the base every future list page (elections,
  finance, donations, ...) will build on rather than reinventing table
  markup each time.
- **Permission-nav fix caught in this phase**: Members was originally
  gated on `hierarchy.manage` only, but the real backend
  (`can_manage_members_at`) also accepts `membership.register` (the
  narrower permission Branch Chairmen/Secretaries hold) — fixed by
  adding OR-permission support (`anyPermissions`) to the nav config
  rather than leaving Branch-level executives unable to see a page they
  actually have API access to. Hierarchy browsing was also over-gated
  (the real `GET` endpoint requires no special permission at all, only
  `POST`/`PATCH`/`DELETE` do) - the nav item is now open to any
  authenticated user, with the mutating actions still correctly gated at
  the page level.



- No known gaps remain against the original scope as of Phase 10.
  Everything in the main navigation is real, including the two
  previously-deferred areas (Polling Agents, Discussion Groups & Direct
  Messages).
- No automated tests yet (no Vitest/Playwright/Testing Library
  configured). Verification so far is: a real `next build` succeeding,
  `tsc --noEmit` clean, `eslint` clean, and `curl`-verified routing/
  redirect/404/static-asset behavior against a real running server.
- **No browser-based visual verification was possible.** This was built
  in a sandboxed environment with no reachable headless-browser binary
  (Playwright's own CDN is outside the network allowlist, same
  constraint as Google Fonts above) — so nothing here has actually been
  *looked at* by a rendering engine, only compiled, type-checked, linted,
  and reviewed by hand. Run `npm run dev` and look at it yourself before
  trusting the visual design holds up; component logic and data-wiring
  are verified, pixel-level layout is not.
- WebSockets are not used anywhere (the backend doesn't have them —
  confirmed by introspection, not assumed); the notification bell polls
  every 30s instead.

## What's built in Phase 3: Departments & Position Management

- **Departments** (`/departments`): browse defined departments, drill into
  a team dashboard for any department at any organizational unit (via the
  same `UnitPicker`, defaulting to the signed-in user's own unit) - real
  roster with per-member pending/completed task counts, upcoming diary,
  **Add Team Member** and **Assign Task** actions wired to the exact
  authority rules confirmed from the backend (HEAD/DEPUTY_HEAD of a
  department at a unit can manage that unit *and every descendant of it*
  — verified against `apps.departments.permissions.has_department_authority`
  rather than assumed).
- **Position Management** (`/settings/positions`): the module the original
  spec explicitly called out. Full `Role` CRUD - create a position, rename
  one, add/remove deputy positions, redefine reporting lines (`reports_to`,
  via a `RolePicker` that excludes the role being edited to prevent an
  obvious self-reference - the backend additionally walks the full chain
  server-side to catch longer cycles), edit its permission tags with a
  real tag input, and retire a position (blocked server-side, surfaced
  client-side, if anyone still actively holds it). `scope` reuses the
  same 19 real unit types as Hierarchy, since a position's scope
  genuinely is an organizational level, not a separate concept.
- **`UserPicker`**: a third reusable combobox (alongside `UnitPicker` and
  `RolePicker`) for assigning department members and task assignees,
  reusing the member-search endpoint rather than a new one.
- **A real React 19 Compiler lint catch, fixed properly, not
  suppressed**: the position edit form originally synced `editingRole`
  into local state (permissions, reports-to) via a `useEffect` that
  called `setState` directly in its body - flagged by the same
  `react-hooks/set-state-in-effect` rule from Phase 1. Rather than
  disabling the rule, I removed the effect entirely: Radix's
  `Dialog.Content` already unmounts from the DOM when closed (no
  `forceMount`), so the form component naturally remounts fresh each
  time the dialog opens, and a lazy `useState(() => editingRole?.x)`
  initializer picks up the current role with no synchronization step
  needed at all - fewer moving parts, not just a quieter linter.

## What's built in Phase 4: Messaging

- **`/messaging`**, three tabs over the real backend endpoints:
  - **Broadcasts** — issue a directive/announcement down your own chain
    of command (gated on `messaging.broadcast.downward`), with
    kind/priority, optional required-acknowledgement, and an
    Acknowledge button that appears exactly when the backend says the
    caller hasn't acknowledged yet.
  - **Reports** — file an upward report to your own unit or any
    ancestor of it, with a detail dialog for the target office (or
    anything above it) to Acknowledge/Resolve with notes - mirrors
    `can_manage_report`'s exact authority rule.
  - **Meetings** — schedule a meeting or workshop; the backend generates
    a **real, working Jitsi Meet room URL** with no external account or
    API key needed, confirmed by reading `generate_meeting_room_url` in
    the backend source rather than assumed. The detail dialog surfaces
    the join link, lets non-hosts RSVP, and shows minutes once a meeting
    is completed.
- Discussion groups and direct messages are intentionally **not** in
  this phase — they're a different UI pattern (a chat interface, not a
  list-and-create-dialog pattern like everything else here) and deserve
  their own focused pass rather than being bolted on to stay "complete."

## What's built in Phase 5: Elections

The biggest single module - `/elections` and `/elections/[id]`, covering
every mechanism the backend supports:

- **Elections & candidates**: create a National General Election,
  Internal Party Election, or Poll; candidates support `party` (for
  multi-party general-election races) and a real photo upload via
  `react-dropzone` (client-side size-checked against the backend's ~2MB
  cap before it ever hits the network, not just after a rejected
  request).
- **Branch collation**: `SubmitResultDialog` requires a photo of the
  physical collation sheet - genuinely required, not optional, matching
  the backend's `collation_sheet_photo_base64` field having no default.
  The submit button is disabled client-side until both a branch and a
  photo are present, backed by the same requirement server-side.
- **Live results & rollups**: point a `UnitPicker` at any unit in the
  hierarchy and the summary recomputes for that subtree in real time via
  the backend's own aggregation - a real Recharts bar chart plus a party
  breakdown, with the four stat cards adapting their fields based on
  whether the backend reports `mode: "BRANCH_COLLATION"` (branches
  reported/turnout) or `mode: "DIRECT_VOTING"` (votes cast/eligible
  count) - two genuinely different data shapes from the same endpoint,
  handled explicitly rather than assumed to match.
- **Direct digital voting** (Internal Party Elections only): an
  `ElectorateManager` tab for the organizer to add eligible voters (they
  get notified server-side), and a `VotingPanel` tab for eligible members
  to actually cast a ballot per race, with per-race "already voted"
  state read directly from `my-eligibility`'s `voted_positions` rather
  than tracked client-side (avoids any risk of the UI claiming a
  successful vote that the backend didn't actually record).
- **Status lifecycle**: DRAFT → OPEN → COLLATION → COMPLETED (or
  CANCELLED from DRAFT/OPEN/COLLATION) surfaced as explicit transition
  buttons matching the real state machine, not a free-form status
  picker that could request an invalid transition.

**Not in this phase**: Polling Agent management (`/elections/agents/*`
API functions are written and typed, ready to use, but no UI consumes
them yet - a real gap, not a silent omission).

## What's built in Phase 6: Finance, Donations, Welfare & Complaints

- **Finance** (`/finance`): a `UnitPicker` (defaulting to the signed-in
  user's own unit) drives both the summary roll-up and the records list
  for that unit's whole subtree — reuses the same `FinanceBreakdownChart`
  built for the dashboard in Phase 1 rather than a second implementation.
  Recording an entry supports a real receipt photo upload; approve/reject
  actions appear inline only on `PENDING` records.
- **Donations** (`/donations`): campaigns with a live progress bar (goal
  vs. pledged vs. fulfilled, from the backend's own aggregation, not
  computed client-side), pledge recording against either a member (via
  `UserPicker`) or a free-text donor name/contact — matching the
  backend's actual "self-pledge vs. on-behalf-of" support — and
  fulfillment, which the backend automatically turns into a real Finance
  record behind the scenes (surfaced in the success toast so it's not a
  silent side effect).
- **Welfare** (`/welfare`): any member can request support for
  themselves with a real supporting-document upload; those with finance
  or hierarchy authority get an optional jurisdiction `UnitPicker` to
  review requests across a subtree, with status-transition buttons that
  match the real state machine (`SUBMITTED → UNDER_REVIEW → APPROVED →
  DISBURSED`, or `REJECTED` from either of the first two) rather than a
  free-form status dropdown.
- **Complaints & Petitions** (`/complaints`): one module for both, since
  the backend models them as the same document with a `complaint_type`
  discriminator — a petition adds a co-sign action (idempotent
  server-side, confirmed by reading `PetitionSupportView`, so double
  clicking doesn't double count) that a plain complaint doesn't show.

## What's built in Phase 7: Events, Documents & Media

- **Events & Campaigns** (`/events`): campaigns group related events under
  one umbrella (matching the backend's actual relationship, not a
  cosmetic grouping); creating an event notifies the target unit's whole
  subtree server-side (confirmed from the view, not assumed) — surfaced
  in the success toast. RSVP is a single upsert-style call, matching the
  backend's "create or update" endpoint rather than separate attend/
  decline endpoints.
- **Documents** (`/documents`): the list view **deliberately omits the
  file payload** per the backend's own design (`PartyDocumentListItemSerializer`
  strips it to keep list responses light) — so downloading fetches the
  detail endpoint on demand rather than pretending the list already had
  the bytes. Upload uses a new generic `FileDropzone` (distinct from the
  image-only `PhotoDropzone` from Phase 5, since a party constitution
  isn't a photo).
- **Media Library** (`/media`): same list/detail split as Documents, for
  the same reason. The gallery deliberately does **not** try to render
  every thumbnail up front (which would mean fetching every asset's full
  payload just to build a grid, the exact N+1 problem the backend's
  split is designed to prevent) — cards show a type icon, and the actual
  image renders only when you open an item. Supports both a direct file
  upload (small media) and an `external_url` (large video), matching the
  backend's own "must provide exactly one" validation rule.

## What's built in Phase 8: Analytics & GIS Map

- **Membership analytics**: real aggregation (total/executive/ordinary
  split, gender breakdown, 12-month growth) rendered with two Recharts
  views - a growth line chart and a gender bar chart - rather than
  raw numbers, since the backend already computes month-by-month
  buckets specifically for charting.
- **Department analytics**: task completion rate and status breakdown
  for any department at any unit, gated on the same OR-authority rule as
  the backend (`hierarchy.manage` OR department HEAD/DEPUTY_HEAD at that
  unit) - confirmed by reading the view, not assumed from the Phase 3
  pattern.
- **GIS map**: real Leaflet (OpenStreetMap tiles, no API key needed),
  fed by the backend's actual GeoJSON `FeatureCollection` endpoint -
  circle markers color-coded by unit type, clicking one links straight
  to that unit's Hierarchy detail page. This is the one genuinely tricky
  integration this phase: **Leaflet touches `window`/`document` when a
  map actually mounts, which breaks Next.js's static prerendering pass**
  if imported directly. Fixed with `next/dynamic(..., { ssr: false })`
  wrapping the actual `MapContainer` — and this was verified working, not
  just theorized: the production build's route table shows `/analytics`
  prerendering as static content (`○`) with zero build errors, which is
  the actual proof the SSR boundary is correctly placed.

## What's built in Phase 9: Settings

- **Profile**: edits exactly the eight fields the backend's `MeView.patch`
  actually accepts (confirmed from source, not guessed) - sending
  anything else would silently be ignored server-side, so the form
  doesn't offer fields that wouldn't save.
- **Security**: password change with a client-side confirm-match check
  ahead of the real request.
- **Notifications**: the three real delivery-channel toggles
  (email/SMS/push) backed by `GET/PUT /messaging/notification-preferences/`
  - each toggle saves independently on change rather than needing a
    separate "Save" button, since the backend already treats this as a
    simple key-value preference object.
- **Appearance**: surfaces the same theme and language switchers built
  into the top nav back in Phase 1, plus a shortcut into Position
  Management for those who have `hierarchy.manage_roles` - not a new
  feature, just a more discoverable home for existing ones.
- **Audit Log**: gated on the same rule as the backend
  (`IsNationalOfficer` - National-scope role or superadmin), with
  action-prefix filtering. This is the platform's first genuinely
  admin-only surface with no equivalent anywhere else in the app.

## What's built in Phase 10: Polling Agents & Chat (Groups + Direct Messages)

This phase closes out the two gaps explicitly named at the end of every
prior phase rather than left implicit.

- **Polling Agents** (new tab on the election detail page): assign party
  agents/presiding-officer-liaisons/observers to a branch, with
  self-service check-in restricted to the assigned agent themselves
  (confirmed from `PollingAgentCheckInView` - even a superadmin checking
  someone else in isn't the intended flow, only self-check-in is, and
  the UI only shows the Check In button when `assignment.agent.id ===
  currentUser.id`).
- **Discussion Groups** (`/messaging/groups`): a genuine chat interface,
  not a repurposed list-and-dialog screen - message bubbles, a
  composer, and membership management (add/remove restricted to the
  group's creator, matching `DiscussionGroupMembersView`'s
  `_require_owner` check exactly). Polls every 8s for new messages in
  the absence of WebSockets (confirmed absent from the backend since
  Phase 1's initial API map).
- **Direct Messages** (`/messaging/direct`): the backend has no
  "conversation" concept - `GET /direct-messages/` just returns every
  message to/from the caller, newest-first. The inbox groups that flat
  list into per-person conversations **client-side**, same approach used
  in the Flutter mobile app for the same endpoint. Opening a thread
  marks unread incoming messages read automatically, one call per
  message via the real per-message endpoint (there's no bulk
  "mark conversation read" endpoint to call instead).

With this phase, there are no more known gaps against the original
scope - every nav destination is real, and both previously-deferred
areas are now built.

## Automated testing

- **Unit/component tests (Vitest + React Testing Library)**: genuinely
  set up, run, and passing - **46 tests across 9 files**, not just
  written and assumed to work. Covers the highest-value, most
  safety-critical logic in the app rather than padding numbers on
  trivial components:
  - `src/lib/permissions.test.ts` - including a regression test for the
    real Phase 2 bug (Members nav item hidden from Branch executives who
    actually had API access via a different permission tag).
  - `src/lib/api/hierarchy.test.ts` - the 20-unit-type catalog and
    parent-type chain logic (main chain vs. TEIN chain vs. auxiliary
    types) that the create-unit dialog depends on.
  - `src/lib/api/client.test.ts` - the Axios error-normalization layer,
    against the real backend error envelope shape.
  - `src/stores/auth-store.test.ts` - specifically covers the rotating-
    refresh-token behavior (`setTokens` must replace *both* tokens
    together, or the session silently breaks after one refresh).
  - `src/hooks/use-debounced-value.test.ts` - using fake timers to
    verify the debounce actually resets on rapid input, not just that it
    delays once.
  - Component tests for `Button`, `EmptyState`, and `OrgUnitPath` (the
    app's signature navigation element).

  Run with `npm test`. Not exhaustive coverage of every file - a
  deliberate choice to test the logic most likely to silently break
  something (permissions, token handling, the hierarchy chain rules)
  over generating tests for every trivial presentational component.

- **E2E tests (Playwright)**: configured and specs written against the
  real app (`e2e/login.spec.ts`, `e2e/navigation.spec.ts`), but
  **honestly unable to run in this sandbox** - there's no reachable
  headless-browser binary to download (`npx playwright install
  chromium` was attempted and silently produced nothing, the same
  network restriction that blocks Google Fonts and the shadcn CLI
  elsewhere in this project). The unauthenticated-routing and 404 specs
  don't need a backend or session and are the safest ones to run first;
  the login and command-palette specs need a real backend and/or a
  storageState auth setup wired in before they'll pass. Don't assume any
  of these pass without running them yourself - `playwright.config.ts`
  has the full caveat at the top.

## Polish: Framer Motion & installability

Two things worth calling out rather than just shipping quietly:

- **Framer Motion was in the original required stack but sat completely
  unused through ten phases** - installed, never imported. Fixed with
  three genuinely tasteful (not gratuitous) additions: `AnimatedNumber`
  (stat cards count up on scroll-into-view, respecting
  `prefers-reduced-motion` by snapping instantly instead of animating
  for anyone who's asked for that), `StaggerContainer`/`StaggerItem`
  (card grids - Dashboard, Elections - fade/slide in with a small
  stagger instead of popping in inert), and `PageTransition` (a subtle
  fade wired into the app shell on every route change). Applied where it
  actually helps legibility, not sprinkled everywhere.
- **A real, working PWA manifest** - `src/app/manifest.ts` (Next.js's
  native file convention, auto-served at `/manifest.webmanifest` and
  verified in this build's own output as a real route, not assumed),
  proper icon set generated from the actual NDC logo (192px, 512px, and
  a padded maskable variant for Android's adaptive-icon safe zone -
  verified by rendering it, not just generating it and hoping), and
  `apple-touch-icon`/`appleWebApp` metadata for iOS home-screen
  installs. This makes the platform installable as a standalone app on
  desktop and mobile without a separate native build.

What this phase deliberately does **not** claim: this isn't a rewrite
into "50 years advanced" territory - that's not a real engineering
target, and I'd rather under-promise here than dress up ordinary,
verifiable improvements in hype. What's here is real: tests that
actually run and pass, and a previously-unused dependency put to
genuine, restrained use.

## Platform assistant chatbot

A floating chat widget (bottom-right, on every authenticated page,
`src/components/chatbot/chat-widget.tsx`) wired to the real backend
endpoints in `apps/chatbot` - available to **every authenticated user
regardless of role**, no permission gate, by design (the whole point was
"all types of users, 24/7").

- Starting the widget for the first time auto-creates a conversation so
  there's no empty "pick a conversation" step; returning users land back
  on their most recent thread.
- A history panel lists past conversations; starting a new one is one
  click away.
- Handles the real 503 the backend returns when `ANTHROPIC_API_KEY`
  isn't configured - shown as an inline warning rather than a generic
  toast, since the user's message was still saved and it's worth saying
  so.
- Reuses the same `MessageBubble`/`ChatComposer` components built for
  Phase 10's discussion-group chat, rather than a second implementation
  of the same chat-bubble UI.
- **A real fix during this build, not suppressed**: the initial
  "auto-select the most recent conversation" logic originally called
  `setState` directly inside a `useEffect` (the same anti-pattern caught
  twice before, in Phase 3 and Phase 8). Fixed by deriving
  `effectiveConversationId` from the query data during render instead of
  storing/syncing it as separate state - only the genuinely-async
  "create a conversation when none exist yet" path still needs an
  effect, since that's an actual side effect (a mutation call), not
  state derivable from data already in hand.
- The system prompt deliberately gives the model **no database access
  and no tool use** - personalization is limited to the calling user's
  own name/role/unit, confirmed by reading `apps/chatbot/services.py` on
  the backend rather than assumed.

## Constitutional realignment (post-launch correction)

After the initial ten build phases, the actual NDC Constitution (a
73-page scanned/vector-graphic PDF, OCR'd page-by-page since it had
almost no extractable text layer) was read and cross-checked against
this platform - a genuinely important discrepancy turned up.

**Article 11 of the Constitution names exactly four official "levels of
organisation": Branch, Constituency, Regional, National.** The platform
had six - `ELECTORAL_AREA` and `ZONE` were invented, not real
constitutional levels. There *is* a real intermediate structure
(Article 17's District Co-ordinating Committee), but it is explicitly
**not** one of the four levels: it only exists in districts spanning
multiple constituencies, has no conference or elected executive of its
own, and its membership is drawn *from* the constituency executives it
coordinates rather than containing them as subordinates.

Fixed by realigning the hierarchy to the real 4-level chain (`NATIONAL →
REGIONAL → CONSTITUENCY → BRANCH`) and moving District Co-ordinating
Committee to the auxiliary-types list (same flexible-attachment pattern
already used for Women's Wing, Youth Wing, Council of Elders, etc.) -
not a 5th rung in the authority chain, exactly matching how the
constitution actually describes it. This was a coordinated change across
**both** the backend (`apps/hierarchy/constants.py`, the seed script's
role list, and every test fixture/case that assumed the old 6-level
chain) and this frontend (`MAIN_CHAIN`/`AUXILIARY_TYPES`, the GIS map's
color legend, nav descriptions, and the unit-type-count assertions in
`hierarchy.test.ts`) - checked the mobile app too and confirmed it never
hardcoded these level names (it treats `unit_type` as a generic string),
so no changes were needed there.

**Verified, not just asserted**: 348/348 backend tests pass, 51/51
frontend tests pass, both real production builds succeed, after this
change - not before it.

Two things worth being explicit about:
- This was read from a **"mini"** constitution - real but possibly
  abridged. TEIN's own internal level names (below "national") and the
  exact scope of `DISTRICT_COORDINATING_COMMITTEE` in the full
  constitution should be re-verified against the complete document if
  available.
- Any already-seeded `ELECTORAL_AREA`/`ZONE` units in a real deployment's
  database would need manual remapping to `BRANCH` (or removal) - there
  was no production data in this build environment to migrate, only
  fixtures and seed scripts, which are updated.

## Disciplinary Committee system (`/discipline`)

After reading the rest of the constitution (previously only ~30 of 73
pages had been read), Articles 46-47 turned out to describe a real,
specific, timed, quasi-judicial process - genuinely distinct from the
general-purpose Complaints module, not something to fold into it. Built
end-to-end: backend (`apps/discipline`, 16 passing tests) and this
frontend.

- **My Cases / Cases / Committee / Suspensions tabs** at `/discipline`,
  plus a dedicated `/discipline/cases/[id]` detail page that walks
  through the actual constitutional lifecycle: report → convene →
  recommend → decide → (optionally) appeal.
- **Deadlines are shown, not hidden**: convene/conclude/appeal deadlines
  come straight from the backend's computed fields and render as visible
  badges/warnings (e.g. "Convene overdue") rather than silently enforced
  server-side rules the user never sees.
- **The 2/3-majority confirmation step is a real UI moment, not a
  checkbox buried in a form**: when an Executive Committee's final
  measure differs from the committee's recommendation, a distinct
  warning panel explains Article 47(9)'s requirement and asks for
  explicit confirmation before the decision can be submitted - matching
  the backend's own refusal to accept a silent override.
- **Elect Committee dialog enforces exactly 3 members** client-side
  before the request even goes out, mirroring the backend's Article
  46(5) validation (which also rejects any candidate who holds an
  executive position at that same unit - surfaced as a clear error
  message if attempted).
- Also renamed to match the constitution exactly, confirmed from the
  full read: `PARLIAMENTARY_CAUCUS` → `PARLIAMENTARY_GROUP`,
  `DIASPORA_CHAPTER` → `EXTERNAL_BRANCH` (Article 10's actual "Integral
  Organs" list) - same rigor as the earlier hierarchy realignment,
  applied consistently rather than treating the first correction as a
  one-off.

## Setup

```bash
cp .env.example .env.local   # point at your running ndc-backend
npm install
npm run dev                  # http://localhost:3000
```

Requires `ndc-backend` running and reachable at the configured
`NEXT_PUBLIC_API_BASE_URL` (see that project's own README for setup —
`docker compose up` is the fastest path).

```bash
npm run build   # production build (Turbopack, verified working)
npm run lint    # eslint
```

## Architecture notes

- **Client-rendered against a separate REST API**, not Next.js Server
  Components fetching data server-side. This is a deliberate choice for
  an admin/dashboard app talking to an existing, separately-deployed
  Django backend — the same architecture the Flutter mobile app
  (`../ndc_mobile`) uses. Pages are `"use client"` and fetch via
  TanStack Query; Server Components are used only where there's no
  interactivity or data dependency (root layout, metadata).
- **`(app)` vs `(auth)` route groups**: `(app)` is auth-gated (redirects
  to `/login` if unauthenticated) and wrapped in the full shell;
  `(auth)` redirects *away* if already authenticated. Both gate on
  `useAuth()`'s `status`, which starts `"unknown"` until session restore
  resolves — this avoids flashing the wrong screen on a hard reload.
- **Permissions**: `src/lib/permissions.ts` mirrors the backend's own
  tag-based model (`hasPermission(user, "hierarchy.manage")`, etc.) for
  UI-level show/hide. This is presentation only — the backend remains
  the actual enforcement boundary on every request, exactly as it should
  be; a hidden nav item is not a security control.
- **Next.js 16 specifics** (this version has real breaking changes vs.
  older docs/training data — see
  `node_modules/next/dist/docs/01-app/02-guides/upgrading/version-16.md`
  in this project for the full list): `middleware` is renamed `proxy`
  (not used here — auth lives client-side in the JWT store, so there's
  no edge-level check to perform); async `params`/`searchParams` only
  applies to Server Components (this app's dynamic routes use client
  components with `useParams()` instead); Turbopack is the default
  bundler for both dev and build.

## Status: feature-complete against original scope

Every module from the original spec is built and real: hierarchy,
members, departments, position management, messaging (broadcasts,
reports, meetings, discussion groups, direct messages), elections
(collation, live results, direct voting, polling agents), events,
finance/donations/welfare/complaints, documents/media, analytics + GIS
map, and settings.

What would come next isn't "the next phase" so much as depth in any one
area: automated tests (Vitest/Playwright), a real browser-based visual
pass (blocked in the sandbox this was built in - see the gap noted
above), and product decisions like whether direct messages need a
proper server-side conversation model instead of the client-side
grouping used here.
