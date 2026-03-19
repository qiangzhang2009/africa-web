import { useState } from 'react'
import { searchHSCodes } from '../utils/api'
import type { HSSearchResult } from '../types'

export default function HSLookupPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<HSSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch() {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchHSCodes(query.trim())
      setResults(data)
      setSearched(true)
    } catch (err: unknown) {
      setError('查询失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">HS编码查询</h1>
        <p className="text-slate-600">输入商品中文名称，智能匹配10位HS税号</p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-8">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="如：咖啡豆、可可豆、腰果"
            className="flex-1 px-4 py-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? '搜索中...' : '查询'}
          </button>
        </div>
        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}
      </div>

      {searched && results.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          <p>未找到相关HS编码，请尝试更通用的关键词</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((item, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-sm bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                    {item.hs_10 || '—'}
                  </span>
                  {item.category && (
                    <span className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full">
                      {item.category}
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-900">{item.name_zh}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs text-slate-500 mb-1">MFN税率</div>
                <div className="text-sm font-semibold text-slate-700">
                  {(item.mfn_rate * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-green-600 mt-0.5">非洲零关税</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Common codes */}
      {!searched && (
        <div>
          <h3 className="font-semibold text-slate-900 mb-4">常用品类</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { name: '咖啡生豆（未烘焙）', code: '0901.21.00' },
              { name: '咖啡熟豆（已烘焙）', code: '0901.21.00' },
              { name: '可可豆（生或焙炒）', code: '1801.00.00' },
              { name: '腰果（未去壳）', code: '0801.31.00' },
              { name: '腰果仁（去壳）', code: '0801.32.00' },
              { name: '铜矿砂', code: '2603.00.00' },
              { name: '钴矿砂', code: '2605.00.00' },
              { name: '锰矿', code: '2602.00.00' },
            ].map((c) => (
              <div key={c.code} className="bg-white rounded-xl border border-slate-200 p-3">
                <p className="text-sm text-slate-900 font-medium">{c.name}</p>
                <p className="text-xs text-slate-500 font-mono mt-1">{c.code}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
