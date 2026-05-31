import React from 'react'
import { semantic, transitions, borderRadius } from '../tokens'

type ButtonVariant = 'primary' | 'secondary' | 'accent' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  fullWidth?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const variantStyles: Record<ButtonVariant, React.CSSProperties> = {
  primary: {
    backgroundColor: semantic.primaryBg,
    color: semantic.primaryText,
    border: 'none',
  },
  secondary: {
    backgroundColor: semantic.secondaryBg,
    color: semantic.secondaryText,
    border: `1px solid ${semantic.secondaryBorder}`,
  },
  accent: {
    backgroundColor: semantic.accentBg,
    color: semantic.accentText,
    border: 'none',
  },
  ghost: {
    backgroundColor: 'transparent',
    color: semantic.bodyColor,
    border: 'none',
  },
  danger: {
    backgroundColor: '#EF4444',
    color: '#FFFFFF',
    border: 'none',
  },
}

const sizeStyles: Record<ButtonSize, React.CSSProperties> = {
  sm: { padding: '0.375rem 0.75rem', fontSize: '0.875rem', gap: '0.375rem' },
  md: { padding: '0.5rem 1rem', fontSize: '1rem', gap: '0.5rem' },
  lg: { padding: '0.75rem 1.5rem', fontSize: '1.125rem', gap: '0.5rem' },
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  children,
  disabled,
  style,
  ...props
}, ref) => {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: '600',
    borderRadius: borderRadius.md,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    transition: `all ${transitions.duration.DEFAULT} ${transitions.easing.DEFAULT}`,
    opacity: disabled ? 0.5 : 1,
    width: fullWidth ? '100%' : 'auto',
    ...variantStyles[variant],
    ...sizeStyles[size],
    ...style,
  }

  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      style={baseStyle}
      {...props}
    >
      {loading ? (
        <span style={{
          width: '1em',
          height: '1em',
          border: '2px solid currentColor',
          borderTopColor: 'transparent',
          borderRadius: '50%',
          animation: 'spin 0.6s linear infinite',
        }} />
      ) : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  )
})

Button.displayName = 'Button'
