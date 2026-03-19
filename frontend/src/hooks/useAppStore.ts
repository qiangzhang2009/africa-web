import { create } from 'zustand'
import type { SubscriptionTier } from '../types'

interface AppState {
  // Subscription
  tier: SubscriptionTier
  dailyFreeQueries: number
  maxFreeDaily: number
  remainingToday: number

  // Actions
  decrementFreeQuery: () => void
  setTier: (tier: SubscriptionTier) => void
  setSubscription: (tier: SubscriptionTier, expiresAt?: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  tier: 'free',
  dailyFreeQueries: 0,
  maxFreeDaily: 3,
  remainingToday: 3,

  decrementFreeQuery: () =>
    set((s) => ({
      remainingToday: Math.max(0, s.remainingToday - 1),
      dailyFreeQueries: s.dailyFreeQueries + 1,
    })),

  setTier: (tier) => set({ tier }),

  setSubscription: (tier) => set({ tier }),
}))
