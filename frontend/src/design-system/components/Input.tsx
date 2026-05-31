import React from 'react'
import { semantic, transitions, borderRadius } from '../tokens'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  style,
  ...props
}, ref) => {
  const [focused, setFocused] = React.useState(false)

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.375rem',
    width: '100%',
  }

  const labelStyle: React.CSSProperties = {
    fontSize: '0.875rem',
    fontWeight: '500',
    color: error ? '#DC2626' : semantic.headingColor,
  }

  const inputWrapperStyle: React.CSSProperties = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  }

  const borderColor = error ? '#EF4444' : focused ? semantic.focusRing : semantic.borderColor
  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.5rem 0.75rem',
    fontSize: '0.9375rem',
    borderRadius: borderRadius.md,
    border: `1px solid ${borderColor}`,
    backgroundColor: '#FFFFFF',
    color: semantic.bodyColor,
    outline: 'none',
    transition: `border-color ${transitions.duration.DEFAULT} ${transitions.easing.DEFAULT}`,
    paddingLeft: leftIcon ? '2.25rem' : undefined,
    paddingRight: rightIcon ? '2.25rem' : undefined,
    ...style,
  }

  const hintStyle: React.CSSProperties = {
    fontSize: '0.75rem',
    color: error ? '#DC2626' : semantic.mutedColor,
  }

  return (
    <div style={containerStyle}>
      {label && <label style={labelStyle}>{label}</label>}
      <div style={inputWrapperStyle}>
        {leftIcon && (
          <span style={{
            position: 'absolute',
            left: '0.75rem',
            color: semantic.mutedColor,
            display: 'flex',
            alignItems: 'center',
            pointerEvents: 'none',
          }}>
            {leftIcon}
          </span>
        )}
        <input
          ref={ref}
          onFocus={(e) => { setFocused(true); props.onFocus?.(e) }}
          onBlur={(e) => { setFocused(false); props.onBlur?.(e) }}
          style={inputStyle}
          {...props}
        />
        {rightIcon && (
          <span style={{
            position: 'absolute',
            right: '0.75rem',
            color: semantic.mutedColor,
            display: 'flex',
            alignItems: 'center',
          }}>
            {rightIcon}
          </span>
        )}
      </div>
      {(error || hint) && <span style={hintStyle}>{error || hint}</span>}
    </div>
  )
})

Input.displayName = 'Input'
