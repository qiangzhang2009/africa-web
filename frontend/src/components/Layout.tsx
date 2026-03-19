import { Link, Outlet, useLocation } from 'react-router-dom'

const navLinks = [
  { to: '/calculator', label: '关税计算器' },
  { to: '/cost-calculator', label: '成本精算' },
  { to: '/hs-lookup', label: 'HS编码查询' },
  { to: '/origin-check', label: '原产地自测' },
  { to: '/policy', label: '政策规则' },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top nav */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">A0</span>
              </div>
              <span className="font-heading text-lg font-bold text-slate-900">
                AfricaZero
              </span>
              <span className="hidden sm:inline text-xs bg-primary-100 text-primary-700 font-medium px-2 py-0.5 rounded-full">
                零关税
              </span>
            </Link>

            {/* Desktop nav */}
            <nav className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                    location.pathname === link.to
                      ? 'bg-primary-50 text-primary-700 font-medium'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {/* CTA */}
            <div className="flex items-center gap-3">
              <Link
                to="/dashboard"
                className="text-sm text-slate-600 hover:text-slate-900"
              >
                我的面板
              </Link>
              <Link
                to="/pricing"
                className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium rounded-lg transition-colors"
              >
                开通 Pro
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile nav */}
      <nav className="md:hidden bg-white border-b border-slate-200 overflow-x-auto">
        <div className="flex px-4 gap-1 py-2">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`whitespace-nowrap px-3 py-1.5 text-sm rounded-lg transition-colors ${
                location.pathname === link.to
                  ? 'bg-primary-50 text-primary-700 font-medium'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main><Outlet /></main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 mt-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 bg-primary-500 rounded-md flex items-center justify-center">
                  <span className="text-white font-bold text-xs">A0</span>
                </div>
                <span className="font-heading text-white font-bold">AfricaZero</span>
              </div>
              <p className="text-sm leading-relaxed">
                全球首款非洲原产地 × 多市场关税套利决策平台。
              </p>
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">产品</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/calculator" className="hover:text-white">关税计算器</Link></li>
                <li><Link to="/cost-calculator" className="hover:text-white">成本精算</Link></li>
                <li><Link to="/hs-lookup" className="hover:text-white">HS编码查询</Link></li>
                <li><Link to="/origin-check" className="hover:text-white">原产地自测</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">资源</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/policy" className="hover:text-white">政策规则</Link></li>
                <li><Link to="/pricing" className="hover:text-white">定价方案</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">联系</h4>
              <ul className="space-y-2 text-sm">
                <li>需要定制官网？</li>
                <li><a href="mailto:hello@africa-zero.com" className="hover:text-white">hello@africa-zero.com</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 mt-8 pt-8 text-sm text-center">
            <p>© 2026 AfricaZero. 数据仅供参考，以官方政策为准。</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
