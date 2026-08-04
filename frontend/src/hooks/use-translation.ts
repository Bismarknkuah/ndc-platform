"use client";

import { useCallback } from "react";
import { useLocaleStore } from "@/stores/locale-store";
import { TRANSLATIONS } from "@/lib/i18n/translations";

export function useTranslation() {
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  const t = useCallback(
    (key: string): string => {
      return TRANSLATIONS[locale]?.[key] ?? TRANSLATIONS.en[key] ?? key;
    },
    [locale],
  );

  return { t, locale, setLocale };
}
