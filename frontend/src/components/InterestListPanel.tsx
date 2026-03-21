import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, X, Calculator, ArrowRight } from 'lucide-react'
import { useAppStore, type InterestItem } from '../hooks/useAppStore'

function InterestCard({ item, onRemove }: { item: InterestItem; onRemove: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-slate-900 text-sm truncate">{item.name}</span>
            <span className="font-mono text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded shrink-0">
              {item.hsCode}
            </span>
            {item.zeroTariff ? (
              <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded-full shrink-0">
                零关税
              </span>
            ) : (
              <span className="text-xs text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded-full shrink-0">
                不适用
              </span>
            )}
          </div>
          <div className="text-xs text-slate-500">
            {item.originCountries.join('、')} · MFN基准{item.mfnRate} · {item.difficulty}
          </div>
        </div>
        <button
          onClick={onRemove}
          className="shrink-0 p-1 text-slate-400 hover:text-red-500 transition-colors"
          title="移除"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link
          to={`/cost-calculator?product=${encodeURIComponent(item.name)}&qty=${item.defaultQty || ''}&price=${item.defaultPrice || ''}&origin=${item.originCountryCodes[0] || ''}`}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium rounded-lg transition-colors"
        >
          <Calculator className="w-3.5 h-3.5" />
          成本精算
        </Link>
        <Link
          to={`/calculator?hs=${item.hsCode}&origin=${item.originCountryCodes[0] || ''}`}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white text-xs font-medium rounded-lg transition-colors"
        >
          关税计算
        </Link>
        <Link
          to={`/origin-check?hs=${item.hsCode}&origin=${item.originCountryCodes[0] || ''}`}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 text-xs font-medium rounded-lg transition-colors"
        >
          原产地自测
        </Link>
      </div>
    </div>
  )
}

export default function InterestListPanel() {
  const { interestList, removeFromInterestList } = useAppStore()
  const [open, setOpen] = useState(false)

  if (interestList.length === 0) return null

  return (
    <>
      {/* Floating trigger */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-primary-500 hover:bg-primary-600 text-white rounded-full shadow-lg shadow-primary-500/30 flex items-center justify-center transition-all hover:scale-105"
        title="我的意向清单"
      >
        <Bookmark className="w-6 h-6" />
        {interestList.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-orange-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
            {interestList.length}
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed inset-0 z-50 flex">
          <div className="flex-1 bg-black/30 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="w-full max-w-md bg-slate-50 h-full overflow-y-auto shadow-2xl flex flex-col">
            <div className="sticky top-0 bg-white border-b border-slate-200 px-5 py-4 flex items-center justify-between">
              <div>
                <h2 className="font-heading font-bold text-slate-900">我的意向清单</h2>
                <p className="text-xs text-slate-500 mt-0.5">{interestList.length} 个品类</p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 p-4 space-y-3">
              {interestList.map((item) => (
                <InterestCard
                  key={item.hsCode}
                  item={item}
                  onRemove={() => removeFromInterestList(item.hsCode)}
                />
              ))}
            </div>

            <div className="sticky bottom-0 bg-white border-t border-slate-200 p-4">
              <Link
                to="/products"
                onClick={() => setOpen(false)}
                className="flex items-center justify-center gap-2 w-full py-2.5 bg-primary-500 hover:bg-primary-600 text-white font-medium rounded-xl transition-colors"
              >
                继续浏览品类
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
