import { Link, Outlet, useLocation } from 'react-router-dom'
import { track } from '../utils/track'
import InterestListPanel from '../components/InterestListPanel'
import { useAppStore } from '../hooks/useAppStore'

const navLinks = [
  { to: '/calculator', label: '关税计算器' },
  { to: '/cost-calculator', label: '成本精算' },
  { to: '/products', label: '选品清单' },
  { to: '/origin-check', label: '原产地自测' },
  { to: '/policy', label: '政策规则' },
  { to: '/getting-started', label: '新手入门' },
]

export default function Layout() {
  const location = useLocation()
  const { isLoggedIn, currentUser, tier: currentTier } = useAppStore()

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top nav */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">A0</span>
              </div>
              <span className="font-heading text-lg font-bold text-slate-900">
                AfricaZero
              </span>
              <span className="hidden sm:inline text-xs bg-orange-100 text-orange-700 font-medium px-2 py-0.5 rounded-full">
                零关税
              </span>
            </Link>

            {/* Desktop nav */}
            <nav className="hidden lg:flex items-center gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                    location.pathname === link.to
                      ? 'bg-orange-50 text-orange-700 font-medium'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            {/* CTA */}
            <div className="flex items-center gap-2">
              {isLoggedIn ? (
                <>
                  <Link
                    to="/account"
                    className="text-sm text-slate-600 hover:text-slate-900 flex items-center gap-1.5"
                  >
                    <div className="w-7 h-7 bg-purple-100 rounded-full flex items-center justify-center">
                      <svg className="w-3.5 h-3.5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                    </div>
                    <span className="hidden sm:inline">{currentUser?.email?.split('@')[0]}</span>
                    <span className={`hidden sm:inline text-xs px-1.5 py-0.5 rounded-full font-medium ${currentUser?.tier === 'enterprise' ? 'bg-purple-100 text-purple-700' : currentUser?.tier === 'pro' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
                      {currentUser?.tier === 'enterprise' ? '企业' : currentUser?.tier === 'pro' ? 'Pro' : '免费'}
                    </span>
                  </Link>
                  {currentUser?.is_admin && (
                    <Link
                      to="/admin"
                      className="text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      管理后台
                    </Link>
                  )}
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="text-sm text-slate-600 hover:text-slate-900"
                  >
                    登录
                  </Link>
                  <Link
                    to="/register"
                    className="text-sm text-slate-600 hover:text-slate-900"
                  >
                    注册
                  </Link>
                </>
              )}
              <Link
                to="/pricing"
                onClick={() => track.pricingCtaClick('pro', 'nav_cta')}
                className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition-colors"
              >
                {isLoggedIn && currentTier !== 'free' ? '续费/升级' : '开通 Pro'}
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile nav */}
      <nav className="lg:hidden bg-white border-b border-slate-200 overflow-x-auto">
        <div className="flex px-4 gap-1 py-2">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`whitespace-nowrap px-3 py-1.5 text-sm rounded-lg transition-colors ${
                location.pathname === link.to
                  ? 'bg-orange-50 text-orange-700 font-medium'
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

      {/* Floating interest list panel */}
      <InterestListPanel />

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 mt-16">
        {/* ZXQConsulting Cross-Promotion Banner */}
        <div className="bg-gradient-to-r from-blue-700 to-indigo-800 py-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-3">
              <div className="w-7 h-7 bg-white/20 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="10"/><path strokeLinecap="round" d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              </div>
              <span className="text-blue-100 text-sm font-medium">
                上海张小强企业咨询 · 您的全球扩张战略合作伙伴
              </span>
            </div>
            <h3 className="text-xl md:text-2xl font-bold text-white mb-3">
              需要专业团队帮您制定全球扩张战略？
            </h3>
            <p className="text-blue-100 text-sm max-w-xl mx-auto mb-6">
              从市场进入策略到落地实施，ZXQConsulting 提供端到端咨询服务。涵盖海外产品进口中国企业、中国企业出口海外市场的双向战略支持。
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <a
                href="https://www.zxqconsulting.com/"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => track.click('footer_zxqconsulting', 'external')}
                className="inline-flex items-center gap-2 bg-white text-blue-700 px-6 py-2.5 rounded-full font-semibold text-sm hover:shadow-xl transition-all hover:scale-105"
              >
                访问 ZXQConsulting 官网
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M12 5l7 7-7 7"/></svg>
              </a>
              <a
                href="https://global2china.zxqconsulting.com/"
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => track.click('footer_global2china', 'external')}
                className="inline-flex items-center gap-2 bg-white/10 text-white border border-white/30 px-6 py-2.5 rounded-full font-semibold text-sm hover:bg-white/20 transition-colors"
              >
                Global2China 进口咨询
              </a>
            </div>
          </div>
        </div>

        {/* Footer Main */}
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
            {/* AfricaZero Brand */}
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 bg-orange-500 rounded-md flex items-center justify-center">
                  <span className="text-white font-bold text-xs">A0</span>
                </div>
                <span className="font-heading text-white font-bold">AfricaZero</span>
              </div>
              <p className="text-sm leading-relaxed">
                全球首款非洲原产地 × 多市场关税套利决策平台。
              </p>
            </div>

            {/* Products */}
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">产品</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/calculator" className="hover:text-white">关税计算器</Link></li>
                <li><Link to="/cost-calculator" className="hover:text-white">成本精算</Link></li>
                <li><Link to="/products" className="hover:text-white">选品清单</Link></li>
                <li><Link to="/origin-check" className="hover:text-white">原产地自测</Link></li>
                <li><Link to="/getting-started" className="hover:text-white">新手入门</Link></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">资源</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/policy" className="hover:text-white">政策规则</Link></li>
                <li><Link to="/pricing" className="hover:text-white">定价方案</Link></li>
                <li><a href="https://www.xe.com/zh-cn/" target="_blank" rel="noopener noreferrer" className="hover:text-white">实时汇率（XE）</a></li>
                <li><a href="https://au-afcfta.org/" target="_blank" rel="noopener noreferrer" className="hover:text-white">AfCFTA 原产地规则</a></li>
                <li><a href="https://www.ccpit.org/" target="_blank" rel="noopener noreferrer" className="hover:text-white">贸促会原产地证书</a></li>
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">联系我们</h4>
              <ul className="space-y-2 text-sm">
                <li>需要搭建独立站或深度定制非洲贸易方案？</li>
                <li><a href="mailto:zxq@zxqconsulting.com" className="hover:text-white">zxq@zxqconsulting.com</a></li>
                <li>微信公众号/视频号:张小强出海</li>
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
