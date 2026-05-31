/**
 * Theme system — light/dark mode configuration.
 * Provides CSS custom property declarations and theme-aware values.
 */
import { colors, semantic, typography, shadows, borderRadius, transitions, zIndex } from './tokens'

export type ThemeMode = 'light' | 'dark' | 'system'

export interface Theme {
  mode: ThemeMode
  colors: Record<string, string>
  typography: typeof typography
  shadows: Record<string, string>
  borderRadius: typeof borderRadius
  transitions: typeof transitions
  zIndex: typeof zIndex
}

// ─── Light Theme ──────────────────────────────────────────────────────────────
export const lightTheme: Theme = {
  mode: 'light',
  colors: semantic,
  typography,
  shadows,
  borderRadius,
  transitions,
  zIndex,
}

// ─── Dark Theme ───────────────────────────────────────────────────────────────
export const darkTheme: Theme = {
  mode: 'dark',
  colors: {
    ...semantic,
    primaryBg: colors.brand[400],
    primaryBgHover: colors.brand[500],
    primaryBgActive: colors.brand[600],
    primaryText: '#FFFFFF',

    secondaryBg: colors.neutral[800],
    secondaryBgHover: colors.neutral[700],
    secondaryBorder: colors.neutral[600],
    secondaryText: colors.neutral[200],

    accentBg: colors.accent[400],
    accentBgHover: colors.accent[500],
    accentText: colors.neutral[900],

    pageBg: colors.neutral[900],
    cardBg: colors.neutral[800],

    headingColor: colors.neutral[50],
    bodyColor: colors.neutral[300],
    mutedColor: colors.neutral[500],

    borderColor: colors.neutral[700],
    borderColorHover: colors.neutral[600],

    focusRing: colors.brand[400],
  },
  typography,
  shadows: {
    ...shadows,
    DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.3), 0 1px 2px -1px rgb(0 0 0 / 0.3)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.3), 0 4px 6px -4px rgb(0 0 0 / 0.3)',
  },
  borderRadius,
  transitions,
  zIndex,
}

// ─── Theme Storage ─────────────────────────────────────────────────────────────

const THEME_STORAGE_KEY = 'africa-zero-theme'

export function getStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'light'
  return (localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode) || 'light'
}

export function setStoredTheme(mode: ThemeMode) {
  if (typeof window === 'undefined') return
  localStorage.setItem(THEME_STORAGE_KEY, mode)
  applyTheme(mode)
}

export function applyTheme(mode: ThemeMode) {
  if (typeof window === 'undefined') return
  const root = document.documentElement
  
  if (mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    root.classList.toggle('dark', prefersDark)
  } else {
    root.classList.toggle('dark', mode === 'dark')
  }
}

// ─── CSS Variables Export ──────────────────────────────────────────────────────

export function injectCSSVariables(theme: Theme) {
  if (typeof document === 'undefined') return
  
  const root = document.documentElement
  
  // Inject as inline style for easy access
  root.style.setProperty('--color-primary', theme.colors.primaryBg)
  root.style.setProperty('--color-primary-hover', theme.colors.primaryBgHover)
  root.style.setProperty('--color-accent', theme.colors.accentBg)
  root.style.setProperty('--color-page-bg', theme.colors.pageBg)
  root.style.setProperty('--color-card-bg', theme.colors.cardBg)
  root.style.setProperty('--color-heading', theme.colors.headingColor)
  root.style.setProperty('--color-body', theme.colors.bodyColor)
  root.style.setProperty('--color-muted', theme.colors.mutedColor)
  root.style.setProperty('--color-border', theme.colors.borderColor)
  root.style.setProperty('--color-focus-ring', theme.colors.focusRing)
}
