import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import CalculatorPage from './pages/CalculatorPage'
import CostCalculatorPage from './pages/CostCalculatorPage'
import HSLookupPage from './pages/HSLookupPage'
import OriginCheckPage from './pages/OriginCheckPage'
import PolicyPage from './pages/PolicyPage'
import PricingPage from './pages/PricingPage'
import DashboardPage from './pages/DashboardPage'
import ProductDiscoveryPage from './pages/ProductDiscoveryPage'
import GettingStartedPage from './pages/GettingStartedPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import AccountPage from './pages/AccountPage'
import AdminPage from './pages/AdminPage'
import FreightPage from './pages/FreightPage'
import CertificatePage from './pages/CertificatePage'
import SuppliersPage from './pages/SuppliersPage'
import { track } from './utils/track'
import { useTrackInit } from './hooks/useTrackInit'
import { useAppStore } from './hooks/useAppStore'
import { getDailyUsage, getMe, getToken } from './utils/api'
import { decodeToken } from './utils/jwt'

function TrackPageView() {
  const location = useLocation()
  useTrackInit()

  useEffect(() => {
    track.page({ path: location.pathname, search: location.search })
  }, [location])

  return null
}

function AuthBootstrap() {
  const { isLoggedIn, updateUser, syncRemainingFromServer, logout } = useAppStore()

  useEffect(() => {
    const token = getToken()
    if (!token) return

    let cancelled = false

    // ── Step 1: INSTANT — decode JWT payload directly (no network call)
    const payload = decodeToken(token)
    if (payload && !cancelled) {
      updateUser({
        id: parseInt(payload.sub),
        email: payload.email,
        tier: payload.tier as 'free' | 'pro' | 'enterprise',
        is_admin: payload.is_admin,
        subscribed_at: null,
        expires_at: null,
        created_at: null,
      })
    }

    // ── Step 2: BACKGROUND (800ms) — verify with server and sync daily usage
    // 800ms delay gives the UI time to become interactive before we hit the cold-start network
    const timer = setTimeout(async () => {
      try {
        const [user, usage] = await Promise.all([
          getMe(),
          getDailyUsage().catch(() => null),
        ])
        if (cancelled) return
        updateUser(user)
        if (usage && typeof usage.remaining_today === 'number' && user.tier === 'free') {
          syncRemainingFromServer(usage.remaining_today)
        }
      } catch (e: unknown) {
        if (cancelled) return
        const status = (e as { response?: { status?: number } })?.response?.status
        if (status === 401) { logout(); return }
        // Network error — we already restored state from JWT above; ignore
      }
    }, 800)

    return () => { cancelled = true; clearTimeout(timer) }
  }, [isLoggedIn, updateUser, logout])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <TrackPageView />
      <AuthBootstrap />
      <Routes>
          <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="calculator" element={<CalculatorPage />} />
          <Route path="cost-calculator" element={<CostCalculatorPage />} />
          <Route path="hs-lookup" element={<HSLookupPage />} />
          <Route path="origin-check" element={<OriginCheckPage />} />
          <Route path="policy" element={<PolicyPage />} />
          <Route path="pricing" element={<PricingPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="products" element={<ProductDiscoveryPage />} />
          <Route path="getting-started" element={<GettingStartedPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="account" element={<AccountPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="freight" element={<FreightPage />} />
          <Route path="certificate" element={<CertificatePage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
