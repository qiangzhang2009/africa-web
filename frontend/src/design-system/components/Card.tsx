import React from 'react'
import { semantic, shadows, borderRadius, transitions } from '../tokens'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'elevated' | 'outlined' | 'flat'
  interactive?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const paddingMap = {
  none: '0',
  sm: '0.75rem',
  md: '1.25rem',
  lg: '1.5rem',
}

export function Card({
  variant = 'elevated',
  interactive = false,
  padding = 'md',
  children,
  style,
  ...props
}: CardProps) {
  const baseStyle: React.CSSProperties = {
    backgroundColor: semantic.cardBg,
    borderRadius: borderRadius.xl,
    padding: paddingMap[padding],
    transition: interactive ? `all ${transitions.duration.DEFAULT} ${transitions.easing.DEFAULT}` : undefined,
    cursor: interactive ? 'pointer' : undefined,
    ...(variant === 'elevated' && { boxShadow: shadows.DEFAULT }),
    ...(variant === 'outlined' && { border: `1px solid ${semantic.borderColor}` }),
    ...(interactive && {
      boxShadow: shadows.DEFAULT,
      border: `1px solid ${semantic.borderColor}`,
    }),
    ...style,
  }

  const [hovered, setHovered] = React.useState(false)
  const hoverStyle: React.CSSProperties = interactive ? {
    boxShadow: shadows.lg,
    transform: 'translateY(-2px)',
    borderColor: semantic.borderColorHover,
  } : {}

  return (
    <div
      style={{ ...baseStyle, ...(hovered ? hoverStyle : {}) }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      {...props}
    >
      {children}
    </div>
  )
}
