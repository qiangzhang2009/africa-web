import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SubscriptionTier } from '../types'

const FREE_DAILY_LIMIT = 3

function getTodayKey() {
  return new Date().toISOString().slice(0, 10)
}

interface DailyCounter {
  date: string
  remaining: number
  totalUsed: number
}

function isNewDay(stored: DailyCounter | null): boolean {
  if (!stored) return true
  return stored.date !== getTodayKey()
}

function makeFreshCounter(): DailyCounter {
  return { date: getTodayKey(), remaining: FREE_DAILY_LIMIT, totalUsed: 0 }
}

// ─── Interest list item ────────────────────────────────────────────────────────
export interface InterestItem {
  hsCode: string
  name: string
  originCountries: string[]
  originCountryCodes: string[]
  mfnRate: string
  zeroTariff: boolean
  difficulty: string
  addedAt: number  // timestamp
  // Pre-filled calc params
  defaultQty?: number
  defaultPrice?: number
}

interface AppState {
  tier: SubscriptionTier
  dailyFreeQueries: number
  maxFreeDaily: number
  remainingToday: number
  counter: DailyCounter

  // Interest list
  interestList: InterestItem[]
  addToInterestList: (item: InterestItem) => void
  removeFromInterestList: (hsCode: string) => void
  isInInterestList: (hsCode: string) => boolean

  decrementFreeQuery: () => void
  setTier: (tier: SubscriptionTier) => void
  setSubscription: (tier: SubscriptionTier, expiresAt?: string) => void
  syncCounter: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      tier: 'free',
      dailyFreeQueries: 0,
      maxFreeDaily: FREE_DAILY_LIMIT,
      remainingToday: FREE_DAILY_LIMIT,
      counter: makeFreshCounter(),

      interestList: [],

      addToInterestList: (item) => {
        const { interestList } = get()
        if (interestList.some(i => i.hsCode === item.hsCode)) return
        set({ interestList: [...interestList, item] })
      },

      removeFromInterestList: (hsCode) => {
        set({ interestList: get().interestList.filter(i => i.hsCode !== hsCode) })
      },

      isInInterestList: (hsCode) => {
        return get().interestList.some(i => i.hsCode === hsCode)
      },

      decrementFreeQuery: () => {
        const { remainingToday, dailyFreeQueries } = get()
        if (remainingToday <= 0) return
        const newRemaining = remainingToday - 1
        const newTotal = dailyFreeQueries + 1
        const newCounter: DailyCounter = {
          date: getTodayKey(),
          remaining: newRemaining,
          totalUsed: newTotal,
        }
        set({ remainingToday: newRemaining, dailyFreeQueries: newTotal, counter: newCounter })
      },

      setTier: (tier) => set({ tier }),

      setSubscription: (tier) => set({ tier }),

      // Call on mount — resets counter if a new day has passed
      syncCounter: () => {
        const { counter } = get()
        if (isNewDay(counter)) {
          const fresh = makeFreshCounter()
          set({ remainingToday: fresh.remaining, dailyFreeQueries: fresh.totalUsed, counter: fresh })
        }
      },
    }),
    {
      name: 'africa-app-store',
      partialize: (state) => ({
        tier: state.tier,
        counter: state.counter,
        dailyFreeQueries: state.dailyFreeQueries,
        interestList: state.interestList,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // After hydration, check if the day has rolled over
          if (isNewDay(state.counter)) {
            const fresh = makeFreshCounter()
            state.remainingToday = fresh.remaining
            state.dailyFreeQueries = fresh.totalUsed
            state.counter = fresh
          } else {
            // Hydrate remainingToday from stored counter
            state.remainingToday = state.counter.remaining
          }
        }
      },
    }
  )
)
