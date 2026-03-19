const policies = [
  {
    market: 'CN',
    flag: '🇨🇳',
    name: '中国零关税政策',
    description: '2026年5月1日起，中国对53个非洲建交国家100%税目零关税。',
    rules: [
      { title: '适用国家', content: '与中国建立外交关系的53个非洲国家（见下方清单）' },
      { title: '税目覆盖', content: '中国税则全部税目（8位编码），覆盖率100%' },
      { title: '生效时间', content: '2026年5月1日零时起' },
      { title: '原产地要求', content: '符合《中华人民共和国海关关于最不发达国家特别优惠关税待遇办法》' },
      { title: '优惠类型', content: '进口关税税率直接降为零，不设配额' },
    ],
    countries: [
      '南非、埃塞俄比亚、安哥拉、贝宁、布隆迪、布基纳法索、佛得角、喀麦隆、中非、乍得、刚果（金）',
      '刚果（布）、科特迪瓦、吉布提、埃及、赤道几内亚、厄立特里亚、斯威士兰、埃斯瓦蒂尼、加蓬',
      '冈比亚、加纳、几内亚、几内亚比绍、肯尼亚、莱索托、利比里亚、马达加斯加、马拉维、马里',
      '毛里塔尼亚、毛里求斯、摩洛哥、莫桑比克、纳米比亚、尼日尔、尼日利亚、卢旺达、塞内加尔、塞舌尔',
      '塞拉利昂、索马里、南苏丹、苏丹、坦桑尼亚、多哥、突尼斯、乌干达、赞比亚、津巴布韦',
    ],
  },
  {
    market: 'EU',
    flag: '🇪🇺',
    name: '欧盟EPA零关税',
    description: '非洲国家与欧盟签署的经济伙伴关系协议（EPA），增值40%以上可享零关税。',
    rules: [
      { title: '适用国家', content: '已签署EPA的非洲国家（科特迪瓦、加纳、喀麦隆等，具体以官方列表为准）' },
      { title: '原产地规则', content: '产品增值≥40%，或符合税号改变规则（CTC）' },
      { title: '关税优惠', content: '税率降至0%' },
      { title: '注意', content: '本页面数据为规则估算，非欧盟官方数据，请以欧盟海关确认为准' },
    ],
    countries: [
      '科特迪瓦、加纳（西非经共体）、喀麦隆（中部非洲）、莫桑比克（南部非洲）等',
    ],
  },
  {
    market: 'AFCFTA',
    flag: '🌍',
    name: 'AfCFTA 非洲大陆自由贸易区',
    description: '非洲内部贸易，关税逐步削减，增值40%以上可享免关税待遇。',
    rules: [
      { title: '参与国', content: '55个非洲联盟成员国（绝大多数已签署）' },
      { title: '增值要求', content: '区内增值≥40%即可享受优惠待遇' },
      { title: '关税削减', content: '分阶段削减，目标在5-15年内实现零关税' },
      { title: '注意', content: '各成员国有过渡期安排，具体税率以各国官方公告为准。本页面数据为估算值。' },
    ],
    countries: ['55个非洲联盟成员国'],
  },
]

export default function PolicyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">政策规则</h1>
        <p className="text-slate-600">中国零关税 · 欧盟EPA · AfCFTA 三大市场规则详解</p>
      </div>

      <div className="space-y-8">
        {policies.map((p) => (
          <div key={p.market} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 border-b border-slate-200 p-6">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">{p.flag}</span>
                <h2 className="text-xl font-heading font-bold text-slate-900">{p.name}</h2>
              </div>
              <p className="text-slate-600 text-sm">{p.description}</p>
            </div>

            <div className="p-6">
              <h3 className="font-semibold text-slate-900 mb-4">规则要点</h3>
              <div className="space-y-3">
                {p.rules.map((rule) => (
                  <div key={rule.title} className="flex gap-3 text-sm">
                    <span className="text-slate-500 shrink-0 w-24 font-medium">{rule.title}</span>
                    <span className="text-slate-700">{rule.content}</span>
                  </div>
                ))}
              </div>

              <h3 className="font-semibold text-slate-900 mt-6 mb-3">适用国家</h3>
              {p.countries.map((line, i) => (
                <p key={i} className="text-sm text-slate-600 mb-1">{line}</p>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <strong>⚠ 免责声明：</strong>本页面政策信息仅供参考。实际通关时，原产地认定、税率适用以中国海关及各目的地国官方公告为准。
        AfricaZero 不对因使用本页面信息导致的任何损失承担责任。如有疑问，请咨询专业报关行或海关。
      </div>
    </div>
  )
}
