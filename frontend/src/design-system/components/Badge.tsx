import React from 'react'
import { borderRadius, transitions } from '../tokens'

type BadgeVariant = 'brand' | 'accent' | 'success' | 'warning' | 'error' | 'info' | 'neutral'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  size?: 'sm' | 'md'
}

const variantStyles: Record<BadgeVariant, React.CSSProperties> = {
  brand: { backgroundColor: '#ECFDF5', color: '#047857', border: '1px solid #A7F3D0' },
  accent: { backgroundColor: '#FEF3C7', color: '#B45309', border: '1px solid #FDE68A' },
  success: { backgroundColor: '#D1FAE5', color: '#065F46', border: '1px solid #A7F3D0' },
  warning: { backgroundColor: '#FEF3C7', color: '#92400E', border: '1px solid #FDE68A' },
  error: { backgroundColor: '#FEE2E2', color: '#991B1B', border: '1px solid #FECACA' },
  info: { backgroundColor: '#DBEAFE', color: '#1E40AF', border: '1px solid #BFDBFE' },
  neutral: { backgroundColor: '#F3F4F6', color: '#374151', border: '1px solid #E5E7EB' },
}

const sizeStyles = {
  sm: { fontSize: '0.6875rem', padding: '0.125rem 0.5rem' },
  md: { fontSize: '0.75rem', padding: '0.25rem 0.625rem' },
}

export function Badge({ variant = 'brand', size = 'sm', children, style, ...props }: BadgeProps) {
  const badgeStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    fontWeight: '500',
    borderRadius: borderRadius.full,
    whiteSpace: 'nowrap',
    transition: `all ${transitions.duration.DEFAULT}`,
    ...variantStyles[variant],
    ...sizeStyles[size],
    ...style,
  }

  return (
    <span style={badgeStyle} {...props}>
      {children}
    </span>
  )
}
