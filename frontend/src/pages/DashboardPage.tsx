import { Link } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'

export default function DashboardPage() {
  const { tier, dailyFreeQueries, maxFreeDaily } = useAppStore()
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
