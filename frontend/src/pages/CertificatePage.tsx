import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  FileText, CheckCircle, ChevronDown,
  Download, Copy, Globe, Shield, Lock, Info, Star,
} from 'lucide-react'
import {
  listCertGuides, getCertGuide, getCertSteps,
  generateCertDocument,
} from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'
import type { CertGuide, CertStepsResponse, CertDocGenerateResult } from '../types'

function StepCard({
  step, isActive, isDone, onClick,
}: {
  step: { step: number; title: string; description: string }
  isActive: boolean
  isDone: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all flex gap-3 ${
        isActive ? 'bg-blue-50 border-blue-300 shadow-sm' : 'bg-white border-slate-200 hover:border-blue-200'
      }`}
    >
      <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
        isDone ? 'bg-green-500 text-white' : isActive ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-600'
      }`}>
        {isDone ? <CheckCircle className="w-4 h-4" /> : step.step}
      </div>
      <div className="flex-1">
        <div className={`font-semibold text-sm ${isActive ? 'text-blue-900' : 'text-slate-700'}`}>
          {step.title}
        </div>
        {isActive && step.description && (
          <div className="text-xs text-blue-700 mt-1 leading-relaxed">{step.description}</div>
        )}
      </div>
      {isActive && <ChevronDown className="w-4 h-4 text-blue-400 shrink-0 mt-1" />}
    </button>
  )
}

export default function CertificatePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isLoggedIn, tier } = useAppStore()

  const [guides, setGuides] = useState<CertGuide[]>([])
  const [selectedCountry, setSelectedCountry] = useState(searchParams.get('country') || 'ET')
  const [guide, setGuide] = useState<CertGuide | null>(null)
  const [steps, setSteps] = useState<CertStepsResponse | null>(null)
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // AI document generation
  const [showDocGen, setShowDocGen] = useState(false)
  const [docResult, setDocResult] = useState<CertDocGenerateResult | null>(null)
  const [docLoading, setDocLoading] = useState(false)
  const [docError, setDocError] = useState('')
  const [processingSteps, setProcessingSteps] = useState('')
  const [materialSources, setMaterialSources] = useState('')
  const [exporterName, setExporterName] = useState('')
  const [importerName, setImporterName] = useState('')
  const [fobValue, setFobValue] = useState('')
  const [quantityKg, setQuantityKg] = useState('')

  useEffect(() => {
    listCertGuides().then(setGuides).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedCountry) return
    setLoading(true)
    setError('')
    setGuide(null)
    setSteps(null)
    setCurrentStep(1)
    Promise.all([
      getCertGuide(selectedCountry),
      getCertSteps(selectedCountry),
    ]).then(([g, s]) => {
      setGuide(g)
      setSteps(s)
    }).catch(() => {
      setError('暂无该国家的办证指南')
    }).finally(() => setLoading(false))
  }, [selectedCountry])

  async function handleGenerateDoc() {
    if (!isLoggedIn) {
      navigate('/login?redirect=/certificate')
      return
    }
    if (tier === 'free') {
      navigate('/pricing')
      return
    }
    setDocLoading(true)
    setDocError('')
    setDocResult(null)
    try {
      const data = await generateCertDocument({
        hs_code: guide?.id ? `0901.11` : '',
        origin_country: selectedCountry,
        processing_steps: processingSteps.split('\n').filter(Boolean),
        material_sources: materialSources.split('\n').filter(Boolean),
        exporter_name: exporterName,
        importer_name: importerName,
        fob_value_usd: parseFloat(fobValue) || 0,
        quantity_kg: parseFloat(quantityKg) || 0,
      })
      setDocResult(data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '生成失败，请稍后重试'
      setDocError(msg)
    } finally {
      setDocLoading(false)
    }
  }

  function copyDoc() {
    if (docResult?.content) {
      navigator.clipboard.writeText(docResult.content)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-green-100 text-green-600 rounded-xl flex items-center justify-center">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-3xl font-heading font-bold text-slate-900">原产地证书办理</h1>
          </div>
        </div>
        <p className="text-slate-600">
          完成关税计算和原产地自测后，在这里获取从非洲出口国办理原产地证书的完整攻略。
          AI 辅助生成办证文件，Pro 版专属功能。
        </p>
      </div>

      {/* Pro upgrade banner */}
      {isLoggedIn && tier === 'free' && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-4 mb-8 flex items-start gap-3">
          <Lock className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-800 mb-1">AI 证书文件生成仅限 Pro 版用户</p>
            <p className="text-xs text-amber-700 mb-3">Pro 版用户每月可免费生成 3 份证书文件，帮助您快速准备办证材料。</p>
            <button
              onClick={() => navigate('/pricing')}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              升级 Pro 版
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left: Country selector */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 sticky top-20">
            <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Globe className="w-4 h-4 text-slate-500" />
              选择原产国
            </h2>
            <div className="space-y-1.5 max-h-[calc(100vh-16rem)] overflow-y-auto pr-1">
              {guides.map(g => (
                <button
                  key={g.id}
                  onClick={() => setSelectedCountry(g.country_code)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all flex items-center gap-2 ${
                    selectedCountry === g.country_code
                      ? 'bg-green-50 border border-green-300 text-green-800 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent'
                  }`}
                >
                  <span className="text-base">{selectedCountry === g.country_code ? '✅' : '🌍'}</span>
                  <span className="flex-1">{g.country_name_zh}</span>
                  {g.api_available && <Star className="w-3 h-3 text-amber-400" />}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Guide content */}
        <div className="lg:col-span-2">
          {loading && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
              <div className="w-8 h-8 border-2 border-green-500/30 border-t-green-500 rounded-full animate-spin mx-auto mb-3" />
              <p className="text-slate-500">加载办证指南...</p>
            </div>
          )}

          {error && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
              <div className="text-4xl mb-3">🌍</div>
              <p className="text-slate-600 mb-4">{error}</p>
              <p className="text-xs text-slate-400">更多国家的办证指南正在陆续添加中</p>
            </div>
          )}

          {guide && steps && (
            <div className="space-y-6">

              {/* Guide header */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">
                      🇪🇹 {guide.country_name_zh} · 原产地证书办理
                    </h2>
                    <p className="text-sm text-slate-500 mt-1">
                      证书类型：{guide.cert_type_zh}（{guide.cert_type}）
                    </p>
                  </div>
                  {guide.api_available && (
                    <span className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-700 text-xs font-medium rounded-full">
                      <Star className="w-3 h-3" /> API 可用
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <div className="text-xs text-slate-500 mb-1">办理机构</div>
                    <div className="text-xs font-medium text-slate-800 leading-snug">{guide.issuing_authority_zh}</div>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <div className="text-xs text-slate-500 mb-1">预计费用</div>
                    <div className="text-sm font-semibold text-slate-800">
                      ${guide.fee_usd_min}-${guide.fee_usd_max} USD
                    </div>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <div className="text-xs text-slate-500 mb-1">办理周期</div>
                    <div className="text-sm font-semibold text-slate-800">
                      {guide.days_min}-{guide.days_max}个工作日
                    </div>
                  </div>
                </div>

                {guide.notes && (
                  <div className="flex gap-2 p-3 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-700">
                    <Info className="w-4 h-4 shrink-0 mt-0.5" />
                    {guide.notes}
                  </div>
                )}

                {guide.website_url && (
                  <div className="mt-3">
                    <a
                      href={guide.website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                    >
                      访问办证机构官网 →
                    </a>
                  </div>
                )}
              </div>

              {/* Steps */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-900 mb-5 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-green-500" />
                  办理流程（{steps.steps.length} 步）
                </h3>
                <div className="space-y-2">
                  {steps.steps.map(step => (
                    <StepCard
                      key={step.step}
                      step={step}
                      isActive={currentStep === step.step}
                      isDone={currentStep > step.step}
                      onClick={() => setCurrentStep(currentStep === step.step ? step.step - 1 : step.step)}
                    />
                  ))}
                </div>
              </div>

              {/* Documents checklist */}
              {steps.documents_required.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 p-6">
                  <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-500" />
                    所需文件清单
                  </h3>
                  <div className="space-y-2">
                    {steps.documents_required.map((doc, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
                        <div className="w-6 h-6 border-2 border-slate-300 rounded-full shrink-0" />
                        <span className="text-sm text-slate-700">{doc}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>我们提供 AI 文件生成功能，可自动生成"出口商声明"和"加工工序说明"，帮您快速准备所需文件。</span>
                  </div>
                </div>
              )}

              {/* AI Document Generation */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-orange-500" />
                    AI 证书文件生成
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-medium">Pro 专属</span>
                  </h3>
                </div>

                {!showDocGen ? (
                  <button
                    onClick={() => {
                      if (!isLoggedIn) navigate('/login?redirect=/certificate')
                      else if (tier === 'free') navigate('/pricing')
                      else setShowDocGen(true)
                    }}
                    className="w-full py-3 border-2 border-dashed border-orange-300 text-orange-600 hover:border-orange-500 hover:bg-orange-50 rounded-xl transition-colors text-sm font-medium"
                  >
                    开始生成证书文件
                  </button>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">出口商名称</label>
                        <input value={exporterName} onChange={e => setExporterName(e.target.value)} placeholder="埃塞俄比亚XX出口公司"
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">进口商名称</label>
                        <input value={importerName} onChange={e => setImporterName(e.target.value)} placeholder="中国XX进口公司"
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">FOB货值 (USD)</label>
                        <input value={fobValue} onChange={e => setFobValue(e.target.value)} placeholder="8000"
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">数量 (kg)</label>
                        <input value={quantityKg} onChange={e => setQuantityKg(e.target.value)} placeholder="2000"
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500" />
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">加工工序（每行一条）</label>
                      <textarea value={processingSteps} onChange={e => setProcessingSteps(e.target.value)}
                        placeholder={"清洗\n分级\n去壳\n装袋"}
                        rows={4}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">原料来源（每行一条，留空默认全本地原料）</label>
                      <textarea value={materialSources} onChange={e => setMaterialSources(e.target.value)}
                        placeholder={"埃塞俄比亚 耶加雪菲产区生豆"}
                        rows={3}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500" />
                    </div>

                    {docError && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{docError}</div>
                    )}

                    <div className="flex gap-3">
                      <button
                        onClick={handleGenerateDoc}
                        disabled={docLoading}
                        className="flex-1 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white font-semibold rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
                      >
                        {docLoading ? (
                          <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />生成中...</>
                        ) : (
                          <><FileText className="w-4 h-4" />生成证书文件</>
                        )}
                      </button>
                      <button onClick={() => setShowDocGen(false)}
                        className="px-4 py-2.5 border border-slate-300 text-slate-600 rounded-xl text-sm hover:bg-slate-50">
                        收起
                      </button>
                    </div>
                  </div>
                )}

                {docResult && (
                  <div className="mt-5">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-slate-800 text-sm">生成的文件预览</h4>
                      <div className="flex gap-2">
                        <button onClick={copyDoc}
                          className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs rounded-lg transition-colors">
                          <Copy className="w-3 h-3" /> 复制
                        </button>
                        <button
                          className="flex items-center gap-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs rounded-lg transition-colors">
                          <Download className="w-3 h-3" /> 下载
                        </button>
                      </div>
                    </div>
                    <pre className="bg-slate-900 text-slate-100 rounded-xl p-5 text-xs overflow-x-auto leading-relaxed max-h-96 overflow-y-auto">
                      {docResult.content}
                    </pre>
                    <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700 flex items-start gap-2">
                      <Info className="w-4 h-4 shrink-0 mt-0.5" />
                      {docResult.usage_note}
                    </div>
                  </div>
                )}
              </div>

              {/* Next steps */}
              <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-2xl p-6">
                <h3 className="font-semibold text-green-900 mb-4">下一步</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <button
                    onClick={() => navigate(`/suppliers?country=${selectedCountry}`)}
                    className="p-4 bg-white border border-green-200 rounded-xl text-left hover:shadow-md transition-shadow"
                  >
                    <div className="text-sm font-semibold text-slate-800 mb-1">🛒 找供应商</div>
                    <div className="text-xs text-slate-500">找到 {guide.country_name_zh} 的认证供应商</div>
                  </button>
                  <button
                    onClick={() => navigate(`/origin-check?origin=${selectedCountry}`)}
                    className="p-4 bg-white border border-green-200 rounded-xl text-left hover:shadow-md transition-shadow"
                  >
                    <div className="text-sm font-semibold text-slate-800 mb-1">🔍 原产地自测</div>
                    <div className="text-xs text-slate-500">验证货物是否符合原产地规则</div>
                  </button>
                  <button
                    onClick={() => navigate(`/cost-calculator?origin=${selectedCountry}`)}
                    className="p-4 bg-white border border-green-200 rounded-xl text-left hover:shadow-md transition-shadow"
                  >
                    <div className="text-sm font-semibold text-slate-800 mb-1">💰 完整成本精算</div>
                    <div className="text-xs text-slate-500">加入物流成本，测算实际利润</div>
                  </button>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  )
}
