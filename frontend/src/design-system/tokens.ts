/**
 * Design tokens — the single source of truth for all design decisions.
 * All colors use hex with alpha support, spacing uses 4px grid.
 */
export const colors = {
  // Primary brand — Emerald green (Africa, growth, sustainability)
  brand: {
    50: '#ECFDF5',
    100: '#D1FAE5',
    200: '#A7F3D0',
    300: '#6EE7B7',
    400: '#34D399',
    500: '#10B981',   // Main brand color
    600: '#059669',   // Primary hover
    700: '#047857',   // Primary active
    800: '#065F46',
    900: '#064E3B',
    950: '#022C22',
  },

  // Accent — Amber/Gold (premium, African sun)
  accent: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    200: '#FDE68A',
    300: '#FCD34D',
    400: '#FBBF24',
    500: '#F59E0B',   // Main accent
    600: '#D97706',   // Accent hover
    700: '#B45309',
    800: '#92400E',
    900: '#78350F',
  },

  // Neutral — Slate gray scale
  neutral: {
    0: '#FFFFFF',
    50: '#F9FAFB',
    100: '#F3F4F6',
    200: '#E5E7EB',
    300: '#D1D5DB',
    400: '#9CA3AF',
    500: '#6B7280',
    600: '#4B5563',
    700: '#374151',
    800: '#1F2937',
    900: '#111827',
    950: '#030712',
  },

  // Semantic colors
  success: {
    light: '#D1FAE5',
    main: '#10B981',
    dark: '#047857',
    text: '#065F46',
  },
  warning: {
    light: '#FEF3C7',
    main: '#F59E0B',
    dark: '#B45309',
    text: '#92400E',
  },
  error: {
    light: '#FEE2E2',
    main: '#EF4444',
    dark: '#DC2626',
    text: '#991B1B',
  },
  info: {
    light: '#DBEAFE',
    main: '#3B82F6',
    dark: '#1D4ED8',
    text: '#1E40AF',
  },
} as const

export const typography = {
  fontFamily: {
    sans: ['Inter', 'Noto Sans SC', 'system-ui', 'sans-serif'].join(', '),
    mono: ['JetBrains Mono', 'Fira Code', 'monospace'].join(', '),
  },
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
    '5xl': '3rem',    // 48px
  },
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
} as const

export const spacing = {
  0: '0',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  1.5: '0.375rem',  // 6px
  2: '0.5rem',      // 8px
  2.5: '0.625rem',  // 10px
  3: '0.75rem',     // 12px
  3.5: '0.875rem',  // 14px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  8: '2rem',        // 32px
  10: '2.5rem',     // 40px
  12: '3rem',       // 48px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
  24: '6rem',       // 96px
} as const

export const borderRadius = {
  none: '0',
  sm: '0.25rem',     // 4px
  DEFAULT: '0.375rem', // 6px
  md: '0.5rem',      // 8px
  lg: '0.75rem',     // 12px
  xl: '1rem',         // 16px
  '2xl': '1.5rem',   // 24px
  full: '9999px',
} as const

export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
} as const

export const transitions = {
  duration: {
    fast: '150ms',
    DEFAULT: '200ms',
    slow: '300ms',
    slower: '500ms',
  },
  easing: {
    DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const

export const zIndex = {
  hidden: -1,
  base: 0,
  raised: 10,
  dropdown: 1000,
  sticky: 1100,
  overlay: 1200,
  modal: 1300,
  toast: 1400,
  tooltip: 1500,
} as const

// ─── Semantic token aliases (for use in components) ──────────────────────────

export const semantic = {
  // Primary button
  primaryBg: colors.brand[500],
  primaryBgHover: colors.brand[600],
  primaryBgActive: colors.brand[700],
  primaryText: '#FFFFFF',

  // Secondary button
  secondaryBg: colors.neutral[50],
  secondaryBgHover: colors.neutral[100],
  secondaryBorder: colors.neutral[200],
  secondaryText: colors.neutral[700],

  // Accent/CTA
  accentBg: colors.accent[500],
  accentBgHover: colors.accent[600],
  accentText: '#FFFFFF',

  // Page background
  pageBg: colors.neutral[50],
  cardBg: '#FFFFFF',

  // Text
  headingColor: colors.neutral[900],
  bodyColor: colors.neutral[700],
  mutedColor: colors.neutral[500],

  // Borders
  borderColor: colors.neutral[200],
  borderColorHover: colors.neutral[300],

  // Focus ring
  focusRing: colors.brand[500],
} as const
