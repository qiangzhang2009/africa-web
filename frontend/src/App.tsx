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

function TrackPageView() {
  const location = useLocation()
  // 初始化追踪 SDK
  useTrackInit()

  useEffect(() => {
    track.page({ path: location.pathname, search: location.search })
  }, [location])

  return null
}

function AuthBootstrap() {
  const { isLoggedIn, updateUser, syncRemainingFromServer } = useAppStore()

  useEffect(() => {
    const token = getToken()
    if (!token) return

    let cancelled = false
    ;(async () => {
      try {
        const [user, usage] = await Promise.all([
          getMe(),
          getDailyUsage().catch(() => null),
        ])
        if (cancelled) return
        // updateUser always succeeds even if getDailyUsage 401'd —
        // a 401 from daily-usage just means the token is expired/invalid,
        // but getMe succeeded so we have the authoritative user state.
        updateUser(user)
        if (usage && typeof usage.remaining_today === 'number') {
          syncRemainingFromServer(usage.remaining_today)
        }
      } catch {
        // Network error — do NOT log out; keep stale UI over a blank screen.
        // On next navigation the effect re-fires and retries.
      }
    })()

    return () => {
      cancelled = true
    }
  }, [isLoggedIn, updateUser, syncRemainingFromServer])

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
