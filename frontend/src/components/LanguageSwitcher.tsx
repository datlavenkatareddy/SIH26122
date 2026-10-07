import React from 'react';
import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { SUPPORTED_LANGUAGES, LANGUAGE_LABELS, setAppLanguage, type SupportedLanguage } from '@/i18n/config';
import { cn } from '@/lib/utils';

interface LanguageSwitcherProps {
  /**
   * 'onDark' (default): sits on AppShell's header, which is always navy
   * regardless of the light/dark theme toggle -- text stays white/60 with
   * a white active pill, matching the existing theme-toggle button there.
   * 'adaptive': sits on a surface that itself switches with the app's
   * light/dark theme (e.g. LoginScreen's white/navy card) -- uses Tailwind
   * dark: variants instead of hardcoded white-on-dark.
   */
  variant?: 'onDark' | 'adaptive';
}

/**
 * Segmented EN / हिं / తె toggle. Changing the language calls i18next's
 * changeLanguage (re-renders every component using useTranslation()
 * immediately, no page reload) and persists the choice to localStorage so
 * it's remembered on next visit -- see i18n/config.ts's getStoredLanguage().
 */
export default function LanguageSwitcher({ variant = 'onDark' }: LanguageSwitcherProps) {
  const { i18n, t } = useTranslation();
  const current = (i18n.language?.split('-')[0] as SupportedLanguage) || 'en';
  const onDark = variant === 'onDark';

  return (
    <div
      className={cn(
        'flex items-center gap-0.5 h-8 px-1 rounded-xl border transition-colors',
        onDark
          ? 'border-white/20 bg-white/5'
          : 'border-slate-300 dark:border-[#1E3A5F] bg-white/95 dark:bg-[#0A2340]/90 shadow-xs backdrop-blur-md'
      )}
      role="group"
      aria-label={t('common.language')}
      title={t('common.language')}
    >
      <Languages className={cn('w-3.5 h-3.5 mx-1 shrink-0', onDark ? 'text-white/70' : 'text-[#071A2D] dark:text-white/70')} />
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => setAppLanguage(lang)}
          title={LANGUAGE_LABELS[lang].english}
          aria-pressed={current === lang}
          className={cn(
            'px-2.5 h-6 rounded-lg text-[11px] font-semibold transition-all',
            current === lang
              ? 'bg-gradient-to-r from-[#FF7A18] to-[#FF941F] text-white shadow-xs font-bold'
              : onDark
              ? 'text-white/75 hover:text-white hover:bg-white/10'
              : 'text-[#071A2D] dark:text-white/70 hover:text-black dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10 font-bold'
          )}
        >
          {LANGUAGE_LABELS[lang].native}
        </button>
      ))}
    </div>
  );
}
