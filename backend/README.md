# NDC Political Party Management Platform — Backend (Phase 0 + Phase 1 complete, plus Events/Finance/Dashboard extensions)

Backend for the National Democratic Congress party management platform:
authentication, role-based access control, the full organizational
hierarchy (National → Branch, TEIN, and every auxiliary structure), a
**departmental chain of command** (Communications, Finance, Organizing,
etc.) that runs parallel to the geographic hierarchy with its own
delegated authority and diary/task assignment, and **digital membership
cards with QR codes**. Built with Django REST Framework + MongoEngine
(MongoDB Atlas), JWT auth, and Redis-backed token revocation.

Everything described below is real and tested — no placeholders, no
mocked endpoints. See "Roadmap" for what's intentionally not built yet.

## Why MongoEngine instead of Djongo

DRF's `ModelSerializer`/`ModelViewSet` conveniences assume Django's
relational ORM. Djongo tries to bridge that gap by translating SQL to Mongo
queries, but it's an unreliable shim that breaks on aggregations, complex
lookups, and newer Django versions. MongoEngine is a first-class Mongo ODM;
the tradeoff is that DRF integration is manual (plain `Serializer` classes
with explicit `create`/`update`, plain `APIView`s instead of
`ModelViewSet`). That's what this codebase does throughout — more code per
endpoint, but nothing hidden or fragile underneath it.

Django's own ORM is kept only for the framework's internal bookkeeping
(SQLite, unused in practice) since Django requires a `DATABASES` setting to
boot. No application data lives there.

## Architecture

```
config/            Django settings, root URLs, WSGI/ASGI
apps/
  core/             Cross-cutting: Mongo connection bootstrap, audit log,
                     pagination, exception handling, request middleware,
                     seed_platform management command
  accounts/         User & Role documents, JWT auth, permissions,
                     registration/login/refresh/logout, role assignment,
                     executive-provisioned member accounts (single + bulk)
  hierarchy/        OrganizationalUnit tree covering the main chain,
                     TEIN's 6 levels, and every auxiliary structure
  departments/      Departmental chain of command (Communications,
                     Finance, Organizing, ...) parallel to the geographic
                     hierarchy, with delegated management authority,
                     diary/task assignments, and a team dashboard
  membership/       Digital membership cards with QR codes, scan-to-verify
  messaging/        Chain-of-command messaging: downward directives,
                     upward reports, discussion groups, direct messages,
                     meetings/workshops with real video rooms, and a
                     unified notification inbox
  elections/        Elections, internal party elections, and polls, with
                     Branch-level (polling-station-level) result
                     collation and automatic real-time roll-up analysis
  events/           Campaigns and events, with RSVP tracking
  finance/          Income/expense tracking with an approval workflow and
                     roll-up summaries at any unit level
  welfare/          Member welfare support requests, auto-linked to
                     finance on disbursement
  complaints/       Complaints and petitions (with co-signing)
  documents/        Party document storage and scoped visibility
  donations/        Fundraising campaigns and pledges (donor tracking,
                     goal progress, auto-linked to finance on fulfillment)
  volunteers/       Volunteer opt-in registry and opportunity signups
  analytics/        Membership/department analytics, GIS map data, and
                     AI-assisted executive summaries (real Claude API call)
  media/            Photo/video/press-clipping library, scoped visibility
  dashboard/        Unified, role-adaptive home-screen endpoint
tests/              pytest suite (338 tests) using mongomock — zero
                     external dependencies required to run
k8s/                Kubernetes manifests (namespace, config, secrets
                     template, Redis, backend Deployment+HPA, Ingress)
```

### Organizational hierarchy model

One `OrganizationalUnit` collection models every structure in the party via
a `unit_type` + self-referencing `parent`:

- **Main chain**: NATIONAL → REGIONAL → CONSTITUENCY → BRANCH (strict
  parent-type validation enforced server-side) — this matches **Article 11
  of the NDC Constitution exactly** ("The Party shall be organised at
  branch, constituency, regional and national level"). An earlier version
  of this hierarchy had two extra invented levels (Electoral Area, Zone)
  that aren't in the constitution; these were removed once the actual
  document was read and cross-checked against the code.
- **TEIN**: TEIN_NATIONAL → TEIN_REGIONAL → TEIN_CAMPUS → TEIN_FACULTY →
  TEIN_DEPARTMENT → TEIN_CLASS (its own strict chain) — TEIN's
  constitutional representation at Regional/Youth/Women conferences is
  confirmed real; its own internal level names below "national" are an
  operational extension, not directly cited in the (mini) constitution
- **Auxiliary bodies** (District Co-ordinating Committee, Women's Wing,
  Youth Wing, Zongo Caucus, External Branches, Parliamentary Group,
  Council of Elders, Functional Committees, Professionals Forum):
  flexible attachment — a `WOMENS_WING` unit whose parent is a `REGIONAL`
  unit *is* that region's Women's Wing. `DISTRICT_COORDINATING_COMMITTEE`
  is real (Article 17) but deliberately modeled here, not as a 5th main
  -chain level - it only exists where a district spans multiple
  constituencies, has no conference or elected executive of its own, and
  its membership is drawn *from* the constituency executives it
  coordinates rather than containing them as subordinates. `EXTERNAL_BRANCH`
  and `PARLIAMENTARY_GROUP` were originally named `DIASPORA_CHAPTER` and
  `PARLIAMENTARY_CAUCUS` respectively - renamed to match Article 10's
  actual "Integral Organs" list exactly once the rest of the constitution
  was read. `PROFESSIONALS_FORUM` is the one type here **not directly
  confirmed** in this (mini) constitution's 73 pages - a reasonable guess
  at a Congress-created organ under Article 10(f), not a citation; worth
  re-checking against the full constitution if available.

`OrganizationalUnit.get_ancestors()` / `get_descendants()` / `is_ancestor_of()`
walk the tree and back every hierarchy-scoped permission check (e.g. a
Regional officer cannot appoint a National officer; a National officer can
manage any unit).

### Roles

`Role` is data, not a hard-coded enum — each row is a position (e.g.
"National Chairman", "Branch Secretary") tagged with a `scope` (which unit
type holds it) and a list of permission codes. New executive positions can
be added via the API without a deployment. `seed_platform` ships a
representative starter set across the main chain, TEIN, and every auxiliary
body — expanded after the full constitutional read to include the
appointed (not elected) national officers confirmed real in Articles
22(9)(m) and 34-37 (Directors of International Relations, Research,
Administration, and Elections, plus the Internal Auditor named as a
standing Finance Committee member), and the four National Committees from
Article 32 that had no equivalent yet (Political, Economic, Social,
Conflict Resolution - Finance/Legal/Communication/Research were already
covered under their operational department names).

### Auth

Stateless JWT (access + refresh), issued/verified without Django's auth app.
Refresh tokens are single-use and rotated; both access and refresh tokens
carry a `jti` that can be blacklisted in Redis on logout, so logout is a
real revocation, not just "forget the token client-side."

### Position Management Module

`Role` is data, not a hard-coded enum — every party position (National
Chairman, Regional Women's Organizer, a brand-new Deputy position that
doesn't exist yet) is a `Role` document with a name, code, scope (which
unit level it's held at), a coarse permission tag list, an optional
`reports_to` (its own reporting line, independent of the geographic
hierarchy — a department head's chain of command isn't always the same
as the branch/region/national tree), and an opaque `dashboard_config`
blob a frontend can read to tailor a role's dashboard without a backend
change. `POST/PATCH/DELETE /api/v1/auth/roles/` let the party create a
new position, rename one, add/remove a deputy, redefine who it reports
to, or retire it (soft-delete, blocked if any active member currently
holds it) — all without touching code. This is deliberately restricted
to **National-level** holders of `hierarchy.manage_roles`
(`can_manage_roles` in `apps.accounts.permissions`) — stricter than the
permission tag alone, because `Role` objects are global, not scoped to a
unit like everything else in this codebase; without that extra check, a
newly created Regional position could be handed enough permission to
edit National-level positions. `reports_to` is validated against both
direct self-reference and longer circular chains (A → B → A) on every
write.

### Member administration

Beyond self-registration and executive-provisioned creation (Phase 0/1),
`GET /api/v1/auth/members/list/?organizational_unit_id=&search=&role_id=&is_active=`
searches/lists members within a jurisdiction (same ancestor-scoped
`hierarchy.manage`/`membership.register` authority used for creating
them — the directory contains national ID numbers and other sensitive
data, so it's not open to ordinary members).
`GET/PATCH /api/v1/auth/members/<id>/` views a profile (self, or authority
over their unit) and suspends/reactivates a member or corrects basic
profile data — the same authority, applied to an existing account rather
than a new one.
`POST /api/v1/auth/members/<id>/transfer/` moves a member to a different
unit (a Branch transfer), requiring authority over **both** the current
and destination unit, so an officer can't move someone out of a
jurisdiction they don't control, or into one they don't control either.

### Audit log

Every meaningful action (login, logout, registration, role assignment,
hierarchy changes) writes to one `AuditLog` collection via
`apps.core.audit.log_action()`. National-level officers can query the full
trail at `GET /api/v1/audit/logs/`.

### Departmental chain of command

A `Department` (Communications, Finance, Organizing, Legal Affairs, Women's
Affairs, Youth Affairs, Elections, Membership, Research & Innovation, IT —
seeded by default, more can be added) runs its **own chain of command in
parallel to the geographic hierarchy**. A `DepartmentAssignment` places a
`User` into a department at a specific `OrganizationalUnit` with a
position (`HEAD`, `DEPUTY_HEAD`, `OFFICER`, `MEMBER`):

- The **National Communications Director** (`HEAD`, Communications, @
  NATIONAL) can add National Communications team `MEMBER`s, appoint or
  remove **Regional Communications Directors**, and — because NATIONAL is
  an ancestor of every unit — reach all the way down to Branch level too.
- A **Regional Communications Director** (`HEAD` @ a REGIONAL unit) can add
  regional team members and manage that department down through their
  region's constituencies/branches, but cannot touch another region or
  appoint anyone at NATIONAL level.
- A **Constituency/district departmental officer** (`HEAD` @ a
  CONSTITUENCY unit) can add/remove that department's Branch-level members
  within their own constituency, on the same rule.

The rule is a single, general one
(`apps.departments.permissions.has_department_authority`): holding
`HEAD`/`DEPUTY_HEAD` for a department at unit U grants management
authority over that department at U *and every descendant of U*. No
special-casing per level — it falls directly out of the
`OrganizationalUnit` tree already built in Phase 0.

**Diary / task assignments** (`TaskAssignment`) let a department head
schedule a member for an engagement — "go on Joy FM's morning show on the
10th" — with an engagement type (TV/Radio/Print/Online/Event/Other),
platform name, location, and scheduled time. The assignee acknowledges or
completes their own tasks; only someone with authority over that member's
unit can cancel or edit one. Every assignment and task action writes to
the audit log.

### Digital membership cards (QR codes)

Every member gets a `MembershipCard` on first request, holding a random,
unguessable `token`. `GET /api/v1/membership/card/` returns the member's
identity plus a base64-encoded PNG QR code (verified in tests to be real,
decodable PNG bytes, not a placeholder). Scanning the code and posting it
to `POST /api/v1/membership/verify/` (e.g. from a registration desk or
polling agent's device) confirms validity and returns the member's name,
role, and unit — without ever exposing the raw membership ID as the
secret. Losing a card is `POST /api/v1/membership/card/reissue/`, which
rotates the token in place so the old QR code stops working immediately.

### Executive-provisioned member accounts (voter/member registration)

Any executive holding `hierarchy.manage` **or** the narrower
`membership.register` permission can create member accounts directly on
someone's behalf rather than waiting for self-registration: `POST
/api/v1/auth/members/` provisions one member at any unit that is their
own unit or a descendant of it - the same ancestor-scoped authority
pattern used everywhere else. This covers two distinct real-world cases:

- A **Constituency ("district") chairman** entering a Branch Chairman /
  Branch Secretary for a branch under their district (`hierarchy.manage`
  - also grants org-structure powers, appropriate for that role).
- A **Branch Chairman/Secretary registering voters/party members in their
  own branch** (`membership.register` - deliberately *narrower* than
  `hierarchy.manage`: it grants registration authority only, not the
  power to create/edit organizational units elsewhere). Seeded onto
  Branch Chairman and Branch Secretary by default.

A one-time temporary password is generated and returned in the response;
the account is flagged `must_change_password`. The same call can
optionally drop the new member straight into a department (`department_id`
+ `department_position`), which additionally requires department
authority over that unit.

**Registration requires real data, not just a name and phone number.**
Because this is an assisted, in-person registration - a branch executive
sitting with a voter/member and filling out their details - the following
are *required*: `gender`, `date_of_birth`, `national_id_number` (Ghana
Card), `residential_address`, `emergency_contact_name`,
`emergency_contact_phone`. `voter_id_number` (Electoral Commission Voter
ID), `occupation`, and `marital_status` are optional. `national_id_number`
and `voter_id_number` are uniquely indexed (sparse, so leaving
`voter_id_number` blank never collides between two different people) -
duplicate registrations are rejected with a clear field-level error before
they ever hit the database. Self-service registration
(`POST /api/v1/auth/register/`) accepts the same fields but keeps them
optional, so signing up yourself stays low-friction.

`POST /api/v1/auth/members/bulk/` does the bulk version of either case -
"enter the branch executives for all the branches in their district" or
register a whole queue of walk-in voters at once - in a single call. Each
entry is validated and authorized independently (HTTP 207 Multi-Status):
one bad entry (duplicate email/ID, wrong unit, missing required field)
doesn't block the rest, and the response reports exactly which entries
succeeded and which failed with why.

A member can also complete/update their own profile's demographic and
contact fields via `PATCH /api/v1/auth/me/`.

### Department team dashboards

`GET /api/v1/departments/dashboard/?department_id=&organizational_unit_id=`
gives the "National Communications team" / "Ashanti Regional
Communications team" / "Kumasi Central district Communications team" view:
the roster with each member's pending/completed task counts, and the
team's upcoming diary. Visible to whoever has authority over that
department+unit, or to a member looking at their own team's dashboard.

### Chain-of-command messaging

**Broadcasts** (`Broadcast`) are downward communications - National → Branch
- and reuse the same authority pattern as departments: issuing a broadcast
to a `target_unit` requires the `messaging.broadcast.downward` role
permission *and* that the issuer's own unit is `target_unit` itself or an
ancestor of it (already seeded onto National Chairman, National Organizer,
Regional Chairman, and several other roles from Phase 0). A broadcast is
either a `DIRECTIVE` (action required) or an `ANNOUNCEMENT`
(informational); every active member in the target subtree gets a
notification, and if `requires_acknowledgement` is set, the issuer can
pull real-time acknowledgement stats (`GET .../acknowledgements/`) showing
who has and hasn't confirmed receipt.

**Reports** (`Report`) are upward communications - Branch → National (or
any ancestor in between). Filing one requires the `messaging.report.upward`
permission; the target unit must be the submitter's own unit or an
ancestor of it (validated server-side, so a report can't be misdirected
sideways). The target office - or anyone above it in the chain - can
acknowledge or resolve it.

**Discussion groups** (`DiscussionGroup` + `GroupMessage`) are freeform,
creator-managed groups (e.g. a campaign strategy team) with membership
control and a message feed, independent of the formal hierarchy.

**Direct messages** (`DirectMessage`) are simple 1:1 internal messaging
with read receipts.

**Notifications** (`Notification`) unify all of the above into one inbox
per user - broadcasts, reports, group messages, direct messages, and
department task assignments all land here, with unread counts and
mark-read/mark-all-read endpoints.

Every broadcast, report, group action, and message write also lands in
the shared `AuditLog` from Phase 0, so National-level oversight sees the
full communication trail, not just the org-structure changes.

### Meetings & training workshops (live video)

`Meeting` covers both regular meetings and training workshops
(`meeting_type`), with a real, working video-conferencing room generated
automatically on creation (`meeting_url`, e.g.
`https://meet.jit.si/NDC-Regional-Comms-Training-x7ab91cd`) - Jitsi Meet's
free public instance, no API key or account signup required. Jitsi
supports screen share and audio/video out of the box, so "trainer shares
their screen and talks to trainees" works immediately by opening that
link.

**Why Jitsi and not custom-built video:** real-time audio/video/screen-share
at scale is a specialized media-server + TURN/STUN infrastructure problem
(bandwidth, NAT traversal, transcoding) - not something any serious
engineering team reimplements from scratch, any more than they'd write
their own payment processor. What this backend owns instead is the part
that's actually specific to the party: *who is allowed to call which
meeting, who's invited, and tracking attendance* - the scheduling,
authority, and RSVP layer around the video room. `generate_meeting_room_url`
in `apps.messaging.services` is a single, swappable function - point it at
a self-hosted Jitsi instance, or replace it with a Zoom/Google Meet API
integration, without touching any other code.

**The calling authority ("chain of channels") is one rule with three
cases**, all in `apps.messaging.permissions.can_call_meeting`:

- **Department meetings** ("the National/Regional/District Communications
  team meeting") are callable two ways: by anyone with department
  authority over that unit (a department HEAD/DEPUTY_HEAD - authority
  cascades down the tree just like team/task management, so "national can
  call regional or district" and "all regional heads can call departmental
  meetings"), **or** by a general jurisdiction executive - a
  Chairman/Secretary - convening a department's meeting within their own
  turf even without personally holding that department role ("district
  executive can call for departmental meetings under their jurisdiction").
- **General (non-departmental) meetings** require jurisdiction authority:
  the caller's own unit must be the target unit or an ancestor of it, and
  their role must carry either `hierarchy.manage` or the narrower
  `meetings.call` permission. `meetings.call` exists specifically for
  roles - like Constituency/District Secretary - that should be able to
  convene meetings without also getting `hierarchy.manage`'s
  organizational-structure and member-provisioning powers. Regional and
  District Chairmen already carry `hierarchy.manage`; Regional Secretary
  does too; District Secretary carries `meetings.call` - so "Regional
  chairman and secretary" and "district chairman or secretary" can all
  call general meetings under their own jurisdiction, with Secretary roles
  deliberately unable to touch the org structure.
- **A meeting for the entire party** (target unit = the National root)
  requires the dedicated `meetings.call_all_members` permission
  specifically - jurisdiction authority alone isn't enough for this one -
  seeded only onto the National Chairman and National General Secretary
  roles: "the party leader or chairman or secretary can call for all
  members."

Invitees get a notification and can `POST .../rsvp/`
(`ATTENDING`/`DECLINED`); the host sees a live attendance summary via
`GET .../rsvps/` and can mark the meeting `LIVE`/`COMPLETED`/`CANCELLED`.

### Elections, polls & result collation

One model (`Election`) covers a national general election, an internal
party election (possibly contesting several positions - Chairman,
Treasurer, ... - in the same event), or a lightweight poll/data-gathering
exercise (`election_type`).

**Organizing authority works at every level, not just National.** Two
independent paths grant `elections.manage`-equivalent authority over a
given `scope_unit`: the National **Election and IT Director** role
(`elections.manage` permission, seeded at NATIONAL scope), or being
HEAD/DEPUTY_HEAD of the **Elections** or **IT** department at that unit or
an ancestor of it - appointed the same way as any other department head,
through `POST /api/v1/departments/assignments/`. A Constituency ("district")
IT director is just someone appointed HEAD of the Elections department at
their Constituency; they automatically get full election-organizing
authority over their own subtree, with zero new code per level.

**Candidates carry real data.** `Candidate` supports `party` (`"NDC"`,
`"NPP"`, `"Independent"`, ...) for multi-party general elections, and
`photo_base64` for a real uploaded photo (same base64-in-Mongo pattern the
membership-card QR codes already use, capped at ~2MB - no external file
storage dependency). `position` groups candidates into separate races
within one election - a single general election contests `"President"`
(one nationwide race) and `"MP - <Constituency>"` (a separate race per
constituency) simultaneously, each tallied independently.

**Two distinct voting mechanisms, one summary endpoint.** Which one an
election uses is auto-detected:

- **Branch-level collation** (general elections): a district/regional/
  national IT director designates *one specific* branch executive as
  that branch's official results submitter - an `Elections`/`IT`
  department `DepartmentAssignment` at that exact Branch, not just "any
  executive there." Only that person can `POST /api/v1/elections/results/`
  for their branch. One submission per (election, branch, position);
  resubmitting returns `409 Conflict` pointing at `PATCH` to amend. A
  district IT director sees every result in their jurisdiction via
  `GET /api/v1/elections/results/?organizational_unit_id=<their unit>`
  (not just one branch at a time), and can mark submissions `VERIFIED` or
  `DISPUTED`; that verification is what "forwarding" to the next level up
  means in practice - the summary endpoint always reflects the current
  state of every level's subtree in real time, so there's no separate
  manual "forward" action to perform.
- **Direct digital voting** (internal party elections): the Election & IT
  Director selects exactly who qualifies - `POST
  /api/v1/elections/<id>/voters/` with a list of user IDs - and each
  newly-eligible member gets a notification. Eligible members check
  `GET /api/v1/elections/<id>/my-eligibility/` and cast their own ballot
  with `POST /api/v1/elections/<id>/vote/` once the election is `OPEN`;
  one vote per race per voter is enforced at the database level, not just
  in application logic, so double-voting is structurally impossible.

**Automatic analysis** is `GET
/api/v1/elections/<id>/results/summary/?organizational_unit_id=&position=`:
point it at any unit - a single Branch, a Constituency, a Region, or
National - and it aggregates every result (from whichever mechanism the
election uses) anywhere in that unit's subtree in real time: per-candidate
and **per-party** totals and percentages (so National can see "who's
winning, NDC or NPP or someone else" directly), the leading candidate,
turnout, and reporting/voting completeness. This is "the system
automatically analyzes the results" - a live, computed picture the moment
results start coming in, without anyone manually adding up sheets or
ballots by hand.

Every branch-level `ResultSubmission` also requires
`collation_sheet_photo_base64` - a photo of the physical result sheet
("pink sheet"), same base64-in-Mongo pattern as candidate photos, capped
at ~2MB. This is the evidentiary backstop for the collation workflow: a
number without a photo of the sheet it came from isn't accepted.

### Meeting minutes

`POST /api/v1/messaging/meetings/<id>/minutes/` - the host records a
summary, decisions, and structured action items (each optionally assigned
to a specific member with a due date) for a meeting. Attendees default to
everyone who RSVP'd `ATTENDING`, or can be set explicitly. Any invitee can
read the minutes; only the host can write them. A second `POST` amends
the existing minutes rather than creating a duplicate.

### Events & campaigns

`Campaign` is an optional umbrella for a set of related `Event`s working
toward a shared goal (a GOTV drive, a membership push); a one-off rally
doesn't need one. Both follow the same ancestor-scoped `hierarchy.manage`
authority as broadcasts - a National officer can organize nationally or
reach down to a single constituency event; a Constituency chairman only
within their own constituency. Creating an event notifies everyone in its
target subtree, and members can RSVP.

### Finance

`FinanceRecord` is one income or expense entry attributed to a specific
organizational unit, with a lightweight approval workflow (`PENDING` →
`APPROVED`/`REJECTED`) gated by the existing `finance.manage`/`finance.view`
permissions (already seeded onto the National Treasurer role from Phase 0).
Entries can carry a receipt photo (same base64 pattern throughout).
`GET /api/v1/finance/summary/?organizational_unit_id=` rolls up total
income, total expense, net balance, and a category breakdown across an
entire subtree - point it at a Branch, a Region, or National for that
level's picture. Defaults to `APPROVED` records only; pass `status=ALL`
to include pending entries.

### Unified dashboard

`GET /api/v1/dashboard/` is one endpoint that adapts to whatever the
caller actually is: every response includes their profile and unread
notification count; a department HEAD additionally sees "teams led"; an
Election & IT Director sees active elections they can manage; anyone
with finance authority sees their unit's finance summary. Sections that
don't apply to the caller are simply absent from the payload rather than
returned empty - the client doesn't need to know anyone's role in advance
to decide what to render.

### Welfare support

`WelfareRequest` lets any member request party support (bereavement,
medical, educational, emergency), filed at their own unit. Finance or
hierarchy authority over that unit (or an ancestor of it) reviews and
approves it, and marking a request `DISBURSED` **automatically creates
the matching `FinanceRecord` expense entry** (category "Welfare Support",
pre-approved) - a welfare payout is never invisible to the books, and
nobody has to remember to enter it twice.

### Complaints & petitions

`Complaint` covers both plain complaints and petitions (`complaint_type`),
addressed to the submitter's own unit or an ancestor of it - the same
rule as upward reports. The target office (or anyone above it) can assign
it to a specific officer and resolve or dismiss it. Petitions additionally
accumulate co-signers via `POST /api/v1/complaints/<id>/support/`
(idempotent - signing twice doesn't double-count).

### Disciplinary Committee system (Articles 46-47)

`apps/discipline` - built after reading the full NDC Constitution and
finding this was a real, specific, quasi-judicial process distinct from
the general-purpose Complaints app above, not something that should be
folded into it:

- **`DisciplinaryCommittee`**: the standing 3-member committee at a unit
  (Article 46(5)) - elected by that unit's Executives, and its members
  must *not themselves hold an executive position there*, which the
  election endpoint actually checks against each candidate's `Role.is_executive`
  before allowing it. Every level has one except the district (a
  `DISTRICT_COORDINATING_COMMITTEE` unit has no Executive of its own to
  elect one, and the endpoint rejects the attempt with a clear error
  naming the article).
- **`DisciplinaryCase`**: the case itself, carrying the constitution's
  actual timelines as computed, always-visible fields rather than
  silent server-side enforcement - `convene_deadline`/`convene_overdue`
  (14 days, Article 47(3)), `conclude_deadline`/`conclude_overdue` (30
  days from convening), and `appeal_deadline` (14 days from decision,
  Article 47(6)/(11)(a)). The lifecycle is
  `REPORTED → CONVENED → RECOMMENDED → DECIDED → (APPEALED) → CLOSED`,
  gated so only the assigned committee's own members can convene/
  recommend and only the Executive Committee (`hierarchy.manage`,
  ancestor-scoped) can record the final decision.
- **Varying a recommendation requires a real confirmation step**: Article
  47(9) requires a 2/3 Executive Committee majority to vary the
  committee's recommended measure. This platform cannot verify a
  real-world vote count, so the decide endpoint requires
  `confirmed_two_thirds_majority: true` explicitly in the request when
  the final measure differs from the recommended one - a deliberate
  confirmation step instead of a silent override, and it's rejected with
  a clear error (naming the article) if omitted.
- **Appeals are modeled as a new case at the parent unit**, linked back
  via `parent_case`, rather than a separate appeal object - because
  Article 47(8) says an appellate committee is "guided by the provisions
  of Articles 45 and 46," i.e. literally the same process one level up.
  Blocked at the National level with a clear "decision is final" message
  (Article 46(11)(a)), and restricted to the respondent themselves.
- **`MemberSuspension`**: the Executive Committee's power to suspend a
  member *before* proceedings even begin (Article 46(1)) if "in the
  interest of the Party" - up to 6 months, must be referred to the
  Disciplinary Committee within one month or it lapses (surfaced via
  `referral_overdue`, not silently auto-lapsed - a failure to act
  shouldn't quietly erase the suspension without anyone noticing),
  renewable exactly once for up to 5 further months (the endpoint
  enforces the single-renewal cap).
- 16 tests covering the full lifecycle, the executive/committee
  membership exclusivity check, the appeal chain, the confirmation
  requirement, and the single-renewal cap.

### Document management

`PartyDocument` stores small-to-medium operational files (constitution,
minutes, forms, policies - capped at ~5MB, same base64-in-Mongo pattern
used throughout) scoped to an organizational unit, with an
`is_public_within_party` flag for things every member should see
regardless of their unit. Visibility follows the same ancestor/descendant
logic as everywhere else: a unit's own subtree can see its documents, and
so can any ancestor. List responses omit the (potentially large) file
payload for performance; fetch the detail view to actually download.
This is deliberately not a full media library - large media (video,
high-res images, large archives) belongs in real object storage
(S3-compatible), which is a separate infrastructure decision outside this
phase's scope.

### Fundraising campaigns & pledges

`FundraisingCampaign` is a dedicated drive with a monetary goal - distinct
from the one-off donations Finance's `INCOME` records already handle.
`Pledge` tracks a commitment from either a member (`donor_user`) or an
external supporter (`donor_name`/`donor_contact`); any member can pledge
for themselves, while campaign authority (`finance.manage` or
`hierarchy.manage`, ancestor-scoped) records pledges on someone else's
behalf. `POST /api/v1/donations/pledges/<id>/fulfill/` records an actual
payment (full or partial) and **automatically creates the matching
FinanceRecord income entry** - the same auto-linking pattern used for
welfare disbursements. `GET /api/v1/donations/campaigns/<id>/progress/`
gives goal-vs-pledged-vs-fulfilled in one call.

### Volunteer coordination

Members opt in via `PUT /api/v1/volunteers/profile/` (skills,
availability). Officers post `VolunteerOpportunity`s - optionally tied to
a specific `Event` - and members sign up
(`POST /api/v1/volunteers/opportunities/<id>/signup/`, idempotent,
auto-creates a volunteer profile if one doesn't exist yet). An
opportunity automatically flips to `FILLED` once signups reach
`needed_count`. Posting a new opportunity notifies everyone in its target
subtree, same as events.

### Analytics & GIS

Three real, computed-from-actual-data endpoints (all gated by
`hierarchy.manage`, ancestor-scoped, since they can surface sensitive
aggregates like gender breakdowns):

- `GET /api/v1/analytics/membership/?organizational_unit_id=` - total
  members, gender breakdown, executive-vs-ordinary split, and
  month-by-month growth over the last 12 months, all real aggregation
  over the actual membership data in that unit's subtree.
- `GET /api/v1/analytics/departments/?department_id=&organizational_unit_id=`
  - task completion rate for a department's team (also open to that
  department's own HEAD/DEPUTY_HEAD, not just general hierarchy
  authority).
- `GET /api/v1/analytics/map/?organizational_unit_id=&unit_type=` - every
  unit with GIS coordinates set, as a GeoJSON `FeatureCollection` ready
  for Leaflet/Mapbox/Google Maps on the client. `OrganizationalUnit` now
  carries optional `latitude`/`longitude` (settable via the existing
  `PATCH /api/v1/hierarchy/units/<id>/`, validated to be set together or
  not at all). This endpoint doesn't guess coordinates or call any
  geocoding service - only units someone has actually pinned show up; the
  map-rendering itself is a frontend concern, appropriately left to a map
  library rather than something to fake server-side.

### SMS, email & push notifications

`apps.messaging.delivery` makes **real** provider calls - Django's SMTP
mail backend for email, Twilio's REST API for SMS, Firebase Cloud
Messaging's HTTP API for push - not simulated success. Every in-app
`Notification` (already built in Phase 1) now also triggers
`dispatch_external()`, which checks each user's `NotificationPreference`
(`GET`/`PUT /api/v1/messaging/notification-preferences/` - email on by
default, SMS/push opt-in) and attempts each enabled channel
independently, so one failing channel (bad phone number, expired push
token) never blocks the others or breaks the request that triggered the
notification.

**Every channel is a clean no-op, logged at INFO, when unconfigured** -
set `EMAIL_HOST_USER`, `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/
`TWILIO_FROM_NUMBER`, or `FCM_SERVER_KEY` (see `.env.example`) to turn on
the corresponding channel. Without real credentials for these third-party
services, delivery genuinely cannot happen - there's no way around that,
and this codebase doesn't pretend otherwise. What's here is real,
correctly-formed integration code that starts working the moment
credentials are supplied, wired through one clean seam
(`send_email`/`send_sms`/`send_push`) so swapping providers later means
editing one file. Production note: these calls are currently synchronous
(they block the request); a production deployment should offload them to
a background task queue (Celery/RQ) rather than making the API response
wait on a third-party HTTP round-trip.

### Media management

`MediaAsset` covers photos, video, audio, and press clippings, with the
same honest storage boundary as documents: small photos can be stored
directly (base64-in-Mongo, capped ~5MB), while video/audio and anything
larger is referenced by `external_url` (YouTube, Vimeo, an S3 bucket, ...)
rather than stored here - exactly one of `file_base64`/`external_url` is
required. Assets can be tagged, optionally linked to an `Event`, and
follow the same subtree/public visibility rule as documents.

### AI-assisted reporting

`POST /api/v1/analytics/ai-report/` turns this platform's own real,
already-computed aggregates (membership analytics, department task
completion, finance summaries - never raw member records) into a concise
executive summary via a **real** call to Anthropic's Messages API. Every
number the model is asked to summarize came from this platform's own
aggregation functions (`apps/analytics/services.py`,
`apps/finance/services.py`) - the prompt explicitly instructs it not to
invent figures. Configure `ANTHROPIC_API_KEY` (see `.env.example`) to turn
this on; without it, the endpoint returns a clear `503` rather than a
fake summary. Every generated report is saved (`AIGeneratedReport`) for
history - `GET /api/v1/analytics/ai-report/?organizational_unit_id=` lists
past reports for a jurisdiction.

### Platform assistant chatbot

`apps/chatbot` - a conversational Q&A assistant available to **every**
authenticated member regardless of role (no permission gate; this
specifically exists to be usable by every type of user, 24/7).
`POST /api/v1/chatbot/conversations/<id>/messages/` sends a message and
gets the assistant's reply synchronously via the same `ANTHROPIC_API_KEY`
configuration as AI-assisted reporting above - both messages (the user's
and the assistant's) come back in one response.

Deliberately scoped for safety, the same way AI-assisted reporting is:
the model is given **no tool use, no function calling, and no database
access** - only the conversation history plus the calling user's own
basic profile (name, role, organizational unit) for personalization. It
cannot look up or discuss anyone else's data because it is never given
the means to; the system prompt explicitly tells it to point people at
the relevant screen (e.g. "check the Analytics page") rather than
guessing a number it doesn't actually have. Conversations are persisted
(`ChatConversation`/`ChatMessage`) so history survives a page reload, and
a dedicated `chat` throttle scope (20/min) bounds cost and abuse
separately from the general `auth` throttle. Returns a clear `503` if
`ANTHROPIC_API_KEY` isn't configured or the provider call fails - the
user's message is still saved either way, nothing is lost.

### Polling agent logistics

`PollingAgentAssignment` is the election-day counterpart to result
collation: who is physically posted to a Branch (polling station) for a
given election, as a Party Agent, Presiding Officer Liaison, or Observer -
distinct from *who may submit the result sheet* (that's the Elections/IT
department designation reused across elections). The agent checks in on
the day themselves (`POST /api/v1/elections/agents/<id>/check-in/`) and
can confirm materials received - real accountability without inventing a
separate materials-tracking subsystem.

### Mobile app (Flutter)

A companion Flutter project (`ndc_mobile/`, sibling to this backend) is a
real, working scaffold: login with JWT storage and automatic token
refresh, the unified dashboard rendered natively, a notification inbox,
the membership card with a real QR code, election browsing and voting,
and event browsing/RSVP - all hitting this actual API, no mock data. It's
intentionally a starting point rather than full feature parity (a native
client covering every module in this backend is its own multi-week
project) - see that project's own README for exactly what's built, what
isn't yet, and setup instructions.



## Running locally

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env      # edit secrets before doing this for real
docker compose up --build
```

This starts the backend, MongoDB, Redis, runs migrations, and seeds base
roles + a bootstrap superadmin (credentials from `.env`,
`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`). API docs at
`http://localhost:8000/api/docs/`. Add `--profile dev-tools` to also start
`mongo-express` at `http://localhost:8081`.

### Option B — Local Python

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# requires a local MongoDB + Redis, or point MONGO_URI/REDIS_URL at hosted ones
python manage.py seed_platform
python manage.py runserver
```

## Running tests

```bash
pytest -q
```

The suite (25 tests, `tests/`) runs against **mongomock** and Django's
in-memory cache — no live MongoDB/Redis needed. This is auto-detected: the
moment Django boots inside a pytest process, `config.settings` switches
Mongo and cache backends automatically, so `pytest` "just works" with zero
environment setup.

```bash
pytest --cov=apps --cov-report=term-missing   # with coverage
flake8 apps config --max-line-length=120 --extend-ignore=E203
black apps config tests
```

## API documentation

Once running: Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/`, raw
OpenAPI 3 schema at `/api/schema/`. Every endpoint below is real and covered
by tests.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/auth/register/` | POST | Self-service Ordinary Member signup |
| `/api/v1/auth/login/` | POST | Issue access + refresh token pair |
| `/api/v1/auth/refresh/` | POST | Rotate access token (old refresh revoked) |
| `/api/v1/auth/logout/` | POST | Revoke a refresh token |
| `/api/v1/auth/me/` | GET/PATCH | Own profile |
| `/api/v1/auth/change-password/` | POST | Change own password |
| `/api/v1/auth/roles/` | GET/POST | List positions / create a position (National-level only) |
| `/api/v1/auth/roles/<id>/` | GET/PATCH/DELETE | View / edit / retire a position (National-level only) |
| `/api/v1/auth/assign-role/` | POST | Appoint/change a member's role (privileged) |
| `/api/v1/auth/members/` | POST | Executive provisions one member account |
| `/api/v1/auth/members/bulk/` | POST | Executive provisions many member accounts at once |
| `/api/v1/auth/members/list/` | GET | Search/list members in a jurisdiction |
| `/api/v1/auth/members/<id>/` | GET/PATCH | View a profile / suspend, reactivate, correct data |
| `/api/v1/auth/members/<id>/transfer/` | POST | Move a member to a different unit |
| `/api/v1/hierarchy/units/` | GET/POST | List/create organizational units |
| `/api/v1/hierarchy/units/<id>/` | GET/PATCH/DELETE | Unit detail, update, soft-delete |
| `/api/v1/hierarchy/units/<id>/descendants/` | GET | Full subtree |
| `/api/v1/hierarchy/units/<id>/ancestors/` | GET | Breadcrumb to root |
| `/api/v1/audit/logs/` | GET | Unified audit trail (National officers only) |
| `/api/v1/departments/` | GET/POST | List / define departments |
| `/api/v1/departments/assignments/` | GET/POST | List / add department team members & directors |
| `/api/v1/departments/assignments/<id>/` | DELETE | Remove a department assignment |
| `/api/v1/departments/my-assignments/` | GET | Caller's own department roles |
| `/api/v1/departments/tasks/` | GET/POST | List / assign diary tasks |
| `/api/v1/departments/tasks/<id>/` | GET/PATCH | View a task; acknowledge/complete/cancel |
| `/api/v1/departments/dashboard/` | GET | Team roster + task stats for a department at a unit |
| `/api/v1/membership/card/` | GET | Own digital membership card + QR code |
| `/api/v1/membership/card/reissue/` | POST | Rotate QR token (lost card) |
| `/api/v1/membership/verify/` | POST | Verify a scanned card |
| `/api/v1/messaging/broadcasts/` | GET/POST | List / issue directives & announcements |
| `/api/v1/messaging/broadcasts/<id>/acknowledge/` | POST | Acknowledge a broadcast |
| `/api/v1/messaging/broadcasts/<id>/acknowledgements/` | GET | Acknowledgement stats (issuer only) |
| `/api/v1/messaging/reports/` | GET/POST | List / file upward reports |
| `/api/v1/messaging/reports/<id>/` | GET/PATCH | View a report; acknowledge/resolve |
| `/api/v1/messaging/groups/` | GET/POST | List / create discussion groups |
| `/api/v1/messaging/groups/<id>/members/` | POST/DELETE | Add / remove a group member |
| `/api/v1/messaging/groups/<id>/messages/` | GET/POST | Group message feed |
| `/api/v1/messaging/meetings/` | GET/POST | List / schedule a meeting or workshop |
| `/api/v1/messaging/meetings/<id>/` | GET/PATCH | View (incl. join link) / reschedule / change status |
| `/api/v1/messaging/meetings/<id>/rsvp/` | POST | RSVP attending/declined |
| `/api/v1/messaging/meetings/<id>/rsvps/` | GET | Attendance summary (host only) |
| `/api/v1/messaging/direct-messages/` | GET/POST | Inbox / send a direct message |
| `/api/v1/messaging/direct-messages/<id>/read/` | POST | Mark a message read |
| `/api/v1/messaging/notifications/` | GET | Notification inbox (`?unread=true`) |
| `/api/v1/messaging/notifications/unread-count/` | GET | Unread count |
| `/api/v1/messaging/notifications/<id>/read/` | POST | Mark one notification read |
| `/api/v1/messaging/notifications/mark-all-read/` | POST | Mark all notifications read |
| `/api/v1/elections/` | GET/POST | List / organize an election, party election, or poll |
| `/api/v1/elections/<id>/` | GET/PATCH | View / update status (OPEN/COLLATION/COMPLETED/...) |
| `/api/v1/elections/<id>/candidates/` | GET/POST | List / add candidates (or poll options) |
| `/api/v1/elections/results/` | GET/POST | List / submit a branch's result sheet |
| `/api/v1/elections/results/<id>/` | GET/PATCH | View / amend a result; verify or dispute |
| `/api/v1/elections/<id>/results/summary/` | GET | Automatic collation & analysis at any unit level |
| `/api/v1/elections/<id>/voters/` | GET/POST | List / select the electorate for direct voting |
| `/api/v1/elections/<id>/voters/<user_id>/` | DELETE | Revoke voting eligibility |
| `/api/v1/elections/<id>/my-eligibility/` | GET | Check your own eligibility & voting status |
| `/api/v1/elections/<id>/vote/` | POST | Cast your ballot (direct digital voting) |
| `/api/v1/messaging/meetings/<id>/minutes/` | GET/POST | View / record meeting minutes |
| `/api/v1/events/campaigns/` | GET/POST | List / organize a campaign |
| `/api/v1/events/campaigns/<id>/` | GET/PATCH | View / update a campaign |
| `/api/v1/events/` | GET/POST | List / organize an event |
| `/api/v1/events/<id>/` | GET/PATCH | View / update an event |
| `/api/v1/events/<id>/rsvp/` | POST | RSVP to an event |
| `/api/v1/events/<id>/rsvps/` | GET | Attendance summary (organizer only) |
| `/api/v1/finance/records/` | GET/POST | List / record income or expense |
| `/api/v1/finance/records/<id>/` | GET/PATCH | View / approve/reject/amend a record |
| `/api/v1/finance/summary/` | GET | Automatic income/expense roll-up at any unit level |
| `/api/v1/dashboard/` | GET | Unified, role-adaptive home screen |
| `/api/v1/welfare/requests/` | GET/POST | List / submit a welfare support request |
| `/api/v1/welfare/requests/<id>/` | GET/PATCH | View / review/approve/disburse |
| `/api/v1/complaints/` | GET/POST | List / file a complaint or petition |
| `/api/v1/complaints/<id>/` | GET/PATCH | View / assign/resolve/dismiss |
| `/api/v1/complaints/<id>/support/` | POST | Co-sign a petition |
| `/api/v1/documents/` | GET/POST | List (no file payload) / upload a document |
| `/api/v1/documents/<id>/` | GET/DELETE | Download (full payload) / soft-delete |
| `/api/v1/donations/campaigns/` | GET/POST | List / organize a fundraising campaign |
| `/api/v1/donations/campaigns/<id>/` | GET/PATCH | View / update a campaign |
| `/api/v1/donations/campaigns/<id>/progress/` | GET | Goal vs pledged vs fulfilled |
| `/api/v1/donations/pledges/` | GET/POST | List / record a pledge |
| `/api/v1/donations/pledges/<id>/fulfill/` | POST | Record a payment (auto-creates a finance record) |
| `/api/v1/volunteers/profile/` | GET/PUT | Manage your own volunteer opt-in |
| `/api/v1/volunteers/opportunities/` | GET/POST | List / post a volunteer opportunity |
| `/api/v1/volunteers/opportunities/<id>/` | GET/PATCH | View / update an opportunity |
| `/api/v1/volunteers/opportunities/<id>/signup/` | POST | Sign up to volunteer |
| `/api/v1/volunteers/opportunities/<id>/signups/` | GET | Volunteer roster (organizer only) |
| `/api/v1/analytics/membership/` | GET | Membership analytics for a jurisdiction |
| `/api/v1/analytics/departments/` | GET | Department task-completion analytics |
| `/api/v1/analytics/map/` | GET | GIS map data (GeoJSON) |
| `/api/v1/analytics/ai-report/` | GET/POST | List / generate an AI executive summary |
| `/api/v1/media/` | GET/POST | List (no file payload) / upload media |
| `/api/v1/media/<id>/` | GET/DELETE | Download (full payload) / soft-delete |
| `/api/v1/elections/agents/` | GET/POST | List / assign a polling agent |
| `/api/v1/elections/agents/<id>/check-in/` | POST | Agent self-checks in on election day |
| `/api/v1/health/` | GET | Health check (verifies MongoDB, unauthenticated) |
| `/metrics` | GET | Prometheus metrics (unauthenticated) |
| `/api/v1/messaging/notification-preferences/` | GET/PUT | Manage your email/SMS/push opt-ins |

## Deployment

- `Dockerfile`: multi-stage build, non-root user, healthcheck, gunicorn
- `docker-compose.yml`: local dev stack (backend + Mongo + Redis + optional
  mongo-express)
- `k8s/`: namespace, ConfigMap, Secret template, Redis, backend
  Deployment+Service+HorizontalPodAutoscaler, TLS Ingress, daily MongoDB
  backup CronJob (`06-backup-cronjob.yaml` - fill in the upload step for
  your storage provider). **Point `MONGO_URI` at your MongoDB Atlas
  connection string in production** — the in-cluster Mongo container in
  `docker-compose.yml` is for local dev only, Atlas is the intended
  production target.
- `.github/workflows/ci.yml`: lint (flake8/black) → test (pytest+coverage)
  → build image, on every push/PR
- `scripts/backup_mongodb.sh` / `scripts/restore_mongodb.sh`: manual
  backup/restore via `mongodump`/`mongorestore` - see `docs/OPERATIONS.md`
  for the full runbook (backups, monitoring, scaling, load testing,
  security), written to actually be followed during an incident, not as
  a policy document nobody reads.

## Security notes for production

- Set real, unique `SECRET_KEY` and `JWT_SECRET` values (never the
  `.env.example` placeholders)
- `DEBUG=False` enables HSTS, SSL redirect, secure cookies, and
  `X-Frame-Options: DENY` automatically (see `config/settings.py`)
- Rotate `JWT_SECRET` periodically; the refresh-token blacklist is
  Redis-backed, so a compromised Redis also needs its own protections
- The `assign-role` endpoint enforces both a permission check *and* an
  organizational-scope check (you can only appoint within your own subtree)
  — don't relax this without understanding the chain-of-command implications

## Roadmap (not yet built)

Done so far (Phase 0 + Phase 1, complete, plus extensions): auth +
hierarchy + infra, departmental chain-of-command + diary/task assignments
+ team dashboards, digital membership cards, chain-of-command messaging
(directives, upward reports, discussion groups, direct messages,
notifications, meeting minutes), executive-provisioned member/voter
accounts (single + bulk, with expanded required data), meetings/training
workshops with real video rooms, elections/polls with multi-level IT
directors, designated branch-level result collation (with photographic
evidence), direct digital voting with electorate selection, multi-party
result breakdowns, and automatic analysis, events & campaigns, finance
(income/expense tracking with approval workflow and roll-up summaries),
welfare support (auto-linked to finance on disbursement), complaints &
petitions, document management, fundraising campaigns & pledges
(auto-linked to finance on fulfillment), volunteer coordination,
membership/department analytics, GIS map data, AI-assisted executive
summaries (real Anthropic API integration), media management, polling
agent logistics, real SMS/email/push delivery integration, error tracking
(Sentry), a real MongoDB-verifying health check, backup/restore tooling
with an operations runbook, Prometheus metrics, a real Locust load-test
script, a unified role-adaptive dashboard, and a Flutter mobile app
covering auth, dashboard, notifications, membership card, elections/
voting, and events/RSVP (`ndc_mobile/`, sibling project). Still to come:

1. Full Flutter feature parity: hierarchy management, department task
   assignment, finance/welfare/complaint entry, campaign management,
   discussion groups, direct messaging screens, volunteer signup,
   analytics/GIS map view
2. Actually running the load test against a real deployment and tuning
   based on results (the script exists; someone still has to run it
   against a staging environment and act on what it finds)
3. A commissioned penetration test (not something this codebase can
   self-certify)
