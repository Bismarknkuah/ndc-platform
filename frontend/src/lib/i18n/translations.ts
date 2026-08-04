export const LOCALES = ["en", "tw", "ee"] as const;
export type Locale = (typeof LOCALES)[number];

export const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  tw: "Twi",
  ee: "Eʋegbe",
};

/**
 * Translation dictionary, built up phase-by-phase alongside the pages
 * that use each string - not speculatively translated ahead of the UI
 * that needs it. Strings not yet present here (most page-level content
 * as of Phase 1) fall back to their English source text via t(), so
 * switching languages never shows a raw missing-key placeholder; it just
 * means that string hasn't been localized yet.
 */
export const TRANSLATIONS: Record<Locale, Record<string, string>> = {
  en: {
    "nav.dashboard": "Dashboard",
    "nav.hierarchy": "Hierarchy",
    "nav.members": "Members",
    "nav.departments": "Departments",
    "nav.messaging": "Messaging",
    "nav.elections": "Elections",
    "nav.events": "Events & Campaigns",
    "nav.volunteers": "Volunteers",
    "nav.finance": "Finance",
    "nav.donations": "Donations",
    "nav.welfare": "Welfare",
    "nav.complaints": "Complaints & Petitions",
    "nav.documents": "Documents",
    "nav.media": "Media Library",
    "nav.analytics": "Analytics",
    "nav.positions": "Position Management",
    "nav.settings": "Settings",
    "auth.login": "Log in",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.loggingIn": "Logging in...",
    "auth.logout": "Log out",
    "common.search": "Search",
    "common.notifications": "Notifications",
    "common.profile": "Profile",
    "common.loading": "Loading...",
    "common.retry": "Retry",
    "common.save": "Save changes",
    "common.cancel": "Cancel",
  },
  tw: {
    "nav.dashboard": "Dashboard",
    "auth.login": "Hyɛn mu",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.logout": "Fi mu",
    "common.search": "Hwehwɛ",
    "common.loading": "Ɛrekɔ so...",
  },
  ee: {
    "nav.dashboard": "Dashboard",
    "auth.login": "Ge ɖe eme",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.logout": "Do go",
    "common.search": "Di nu",
    "common.loading": "Ele edzi yim...",
  },
};
