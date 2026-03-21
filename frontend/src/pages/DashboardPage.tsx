import { Link } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'
import { Bookmark } from 'lucide-react'

export default function DashboardPage() {
  const { tier, dailyFreeQueries, maxFreeDaily, interestList } = useAppStore()
  const isPro = tier !== 'free'

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">我的面板</h1>
      <p className="text-slate-600 mb-8">管理订阅、查看计算历史</p>

      {/* Subscription status */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 mb-1">当前方案</h2>
            <p className="text-sm text-slate-500">
              {isPro ? `Pro 版会员` : '免费版'}
            </p>
          </div>
          {!isPro && (
            <Link
              to="/pricing"
              className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              升级 Pro
            </Link>
          )}
        </div>

        {!isPro ? (
          <div>
            <div className="flex justify-between text-sm text-slate-600 mb-1">
              <span>今日已使用</span>
              <span>{dailyFreeQueries} / {maxFreeDaily} 次</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all"
                style={{ width: `${(dailyFreeQueries / maxFreeDaily) * 100}%` }}
              />
            </div>
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 text-sm font-medium px-3 py-1.5 rounded-lg">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Pro 版 · 无限次使用
          </div>
        )}
      </div>

      {/* Interest list */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bookmark className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold text-slate-900">我的意向清单</h2>
          </div>
          <Link
            to="/products"
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            继续浏览 →
          </Link>
        </div>
        {interestList.length === 0 ? (
          <div className="text-center py-6">
            <p className="text-sm text-slate-500 mb-3">还没有意向品类</p>
            <Link
              to="/products"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              浏览选品清单
            </Link>
          </div>
        ) : (
          <div>
            <p className="text-sm text-slate-600 mb-3">
              共 <strong>{interestList.length}</strong> 个品类
            </p>
            <div className="space-y-2">
              {interestList.slice(0, 5).map((item) => (
                <div key={item.hsCode} className="flex items-center gap-3 p-2.5 bg-slate-50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-800 truncate">{item.name}</span>
                      <span className="font-mono text-xs text-slate-400">{item.hsCode}</span>
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {item.originCountries[0]} · {item.difficulty}
                    </div>
                  </div>
                  <Link
                    to={`/cost-calculator?product=${encodeURIComponent(item.name)}&qty=${item.defaultQty || ''}&price=${item.defaultPrice || ''}&origin=${item.originCountryCodes[0] || ''}`}
                    className="shrink-0 px-2.5 py-1 bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium rounded-lg transition-colors"
                  >
                    精算
                  </Link>
                </div>
              ))}
            </div>
            {interestList.length > 5 && (
              <p className="text-xs text-slate-400 mt-2 text-center">
                还有 {interestList.length - 5} 个品类...
              </p>
            )}
          </div>
        )}
      </div>

      {/* History */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">计算历史</h2>
        {dailyFreeQueries === 0 && !isPro ? (
          <div className="text-center py-8 text-slate-500">
            <p className="text-sm">还没有计算记录</p>
            <Link to="/calculator" className="text-primary-600 text-sm mt-1 inline-block">
              前往计算 →
            </Link>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            <p className="text-sm">历史记录功能开发中</p>
            <p className="text-xs mt-1">Pro 版上线后解锁完整历史记录</p>
          </div>
        )}
      </div>
    </div>
  )
}
