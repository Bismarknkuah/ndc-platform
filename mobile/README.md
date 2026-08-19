# NDC Member Portal — Mobile (Flutter)

A real, working Flutter client for the [`ndc-backend`](../ndc-backend) API:
login, a role-aware unified dashboard, and a notification inbox. This is a
**starting scaffold, not full feature parity** with the backend — see
"Scope" below for exactly what that means and what's intentionally not
here yet.

## What's actually built and working

- **Auth** (`lib/features/auth/`): real login against
  `POST /api/v1/auth/login/`, JWT access/refresh tokens stored in
  `flutter_secure_storage` (OS keychain/keystore, not plaintext prefs),
  automatic silent token refresh on a 401 via a Dio interceptor
  (`lib/core/api_client.dart`), and logout that revokes the refresh token
  server-side.
- **Dashboard** (`lib/features/dashboard/`): calls the real
  `GET /api/v1/dashboard/` endpoint and renders whichever sections the
  backend actually returns for that user's role — an Ordinary Member sees
  their profile and upcoming meetings; someone who leads a department
  team additionally sees "Teams You Lead"; an Election & IT Director sees
  active elections; someone with finance authority sees a finance summary.
  No client-side role branching — the UI just renders what's present.
- **Notifications** (`lib/features/notifications/`): real list from
  `GET /api/v1/messaging/notifications/`, tap-to-mark-read, mark-all-read,
  pull-to-refresh.
- **Profile tab**: shows the logged-in member's real data and logs out.
- **Membership Card** (`lib/features/membership/`): real QR code from
  `GET /api/v1/membership/card/`, decoded and rendered natively
  (`Image.memory`), with a confirm-then-reissue flow for lost cards.
- **Elections & Polls** (`lib/features/elections/`): browse elections,
  view candidates grouped by race (photos included when set), see your
  own eligibility, and cast a real vote via
  `POST /api/v1/elections/<id>/vote/` when eligible and the election is
  open - each race tracks its own already-voted state independently.
- **Events** (`lib/features/events/`): browse upcoming events and RSVP
  (Attending/Can't make it) via the real endpoint.
- **Volunteer** (`lib/features/volunteers/`): browse open opportunities
  and sign up in one tap; shows filled/needed counts.
- **Welfare Support** (`lib/features/welfare/`): submit a real welfare
  request (category, description, amount) and see your own request
  history with live status.
- **Discussion Groups** (`lib/features/groups/`): list your groups,
  create new ones, and a real chat feed per group.
- **Messages** (`lib/features/direct_messages/`): a 1:1 inbox derived
  client-side from the flat message list the backend exposes (there's no
  dedicated conversations endpoint), and a real chat screen per
  conversation with sent/received message bubbles.

Every screen hits the real backend — there is no mock data or fake
delay-then-show-placeholder anywhere in this code.

## Scope — what's *not* here yet

Building a mobile client with full feature parity to everything in
`ndc-backend` (hierarchy management, department task assignment, branch
result-sheet submission with photo upload, meeting video calls/minutes,
finance entry, complaint/petition filing, campaign management, media
library, analytics/GIS map view) is realistically its own multi-week
project — dozens of screens, forms, and flows. This scaffold now covers
login, the unified dashboard, notifications, the membership card,
election browsing/voting, event browsing/RSVP, volunteer signup, welfare
requests, discussion groups, and direct messaging - the architecture (API
client, token handling, provider-based state management, model pattern)
is in place to add the rest screen-by-screen. Ask for specific screens
next and they'll be built the same way: real API
calls, no placeholders.

## Platform support: Android and iOS, from one codebase

This is a genuinely cross-platform app, not an Android-first build with
iOS bolted on. Every line in `lib/` is plain Dart/Flutter widget and
business logic — confirmed zero use of `dart:io`'s `Platform.isAndroid`/
`Platform.isIOS` or any platform channel anywhere in the codebase, so
there is no platform-specific branching to go stale or diverge between
the two. The app also doesn't touch any native capability that needs
special per-platform permission setup (no camera, location, push tokens,
or biometrics yet) — it's HTTP calls (Dio) and secure key-value storage
(`flutter_secure_storage`, which itself wraps Android's Keystore and
iOS's Keychain transparently). The single `flutter create
--platforms=android,ios` command below generates *both* native shells
from this one Dart codebase; there is no separate iOS branch or fork to
maintain.

**What you still need for each platform, same as any Flutter app:**

- **Android**: Android Studio (or just the Android SDK command-line
  tools) and a connected device/emulator. No Mac required.
- **iOS**: a Mac with Xcode installed (Apple's own toolchain requirement
  for building iOS apps — this isn't a Flutter limitation, every iOS app
  needs Xcode present on the build machine), plus CocoaPods
  (`sudo gem install cocoapods`) for native dependency management, which
  `flutter create` wires up automatically. Running on a physical iPhone
  additionally needs an Apple Developer account for code signing;
  the iOS Simulator (bundled with Xcode) works without one for
  development.

## Project setup

This repository ships `pubspec.yaml` and `lib/`, but **not** the
platform-specific `android/` and `ios/` directories — those are
generated, largely boilerplate scaffolding that Flutter's own tooling
produces (and which this sandbox can't run, since it has no Flutter SDK
and no network access to Google's package/tooling servers). Generate them
yourself in one step:

```bash
# From this directory - generates BOTH native shells at once:
flutter create --platforms=android,ios --org com.ndc .
flutter pub get
```

This will *not* overwrite `lib/`, `pubspec.yaml`, or `test/` — `flutter
create` only fills in what's missing (the platform folders).

### Point the app at your backend

The API base URL is compiled in via a Dart define, defaulting to
`http://10.0.2.2:8000/api/v1` (the standard address for the Android
emulator to reach its host machine's `localhost`):

```bash
# Android emulator (default, no flag needed):
flutter run

# iOS simulator (can use localhost directly):
flutter run --dart-define=NDC_API_BASE_URL=http://localhost:8000/api/v1

# Physical device on the same network as your machine:
flutter run --dart-define=NDC_API_BASE_URL=http://<your-computer-ip>:8000/api/v1
```

Make sure `ndc-backend` is actually running first (`docker compose up` in
that project) and reachable from wherever you're running the app.

### Run tests

```bash
flutter test
```

Two widget tests ship in `test/login_screen_test.dart` covering the login
form's rendering and validation, plus unit tests in
`test/model_parsing_test.dart` covering the election/event JSON model
parsing (including edge cases like missing optional fields).

## Architecture notes

- **State management**: `provider` + `ChangeNotifier`. Kept intentionally
  simple over Bloc/Riverpod for a scaffold this size; swap it out if the
  team has a different standard.
- **API client** (`lib/core/api_client.dart`): one Dio instance, one place
  that knows about JWTs. Every feature provider calls `ApiClient.instance`
  and gets back plain `Map<String, dynamic>` — models parse that, the
  client never leaks Dio types into feature code.
- **Models** (`lib/models/`): plain Dart classes with `fromJson` factories,
  not code-generated (no `json_serializable`/build_runner step to manage
  for a project this size yet — revisit if the model surface grows a lot).
- **Error handling**: the backend's `{"error": {"code", "message"}}`
  envelope is unwrapped into `ApiException` in one place
  (`ApiClient._asApiException`), so every screen can just catch
  `ApiException` and show `error.message` directly.

## A note on verification

This code was written carefully but **could not be run through
`flutter analyze`, `flutter test`, or `flutter build`** in the environment
it was produced in (no Flutter SDK, and the Dart/Flutter package servers
aren't reachable from that sandbox's network allowlist). Every file was
reviewed by hand for syntax and API correctness against Dio 5.x /
Provider 6.x / flutter_secure_storage 9.x APIs, but you should run
`flutter analyze` yourself as a first step after setup, before assuming
it's 100% clean.
