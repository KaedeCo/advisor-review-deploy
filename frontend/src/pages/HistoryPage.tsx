import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import * as api from '../services/api'

/** 给相对路径补全 GradChoice 域名 */
function fullUrl(path: string) {
  if (!path) return ''
  return path.startsWith('http') ? path : `https://gradchoice.org${path}`
}

/** 安全解析 platforms_used（兼容 string / array） */
function parsePlatforms(val: unknown): string[] {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') {
    try { const p = JSON.parse(val); return Array.isArray(p) ? p : [] } catch { return [] }
  }
  return []
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<api.HistoryRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [detailId, setDetailId] = useState<number | null>(null)
  const [detailData, setDetailData] = useState<api.HistoryDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => { loadHistory() }, [])

  async function loadHistory() {
    setLoading(true)
    try {
      const data = await api.fetchHistory()
      setRecords(data.records)
      setTotal(data.total)
    } catch (e) { console.error(e) } finally { setLoading(false) }
  }

  async function loadDetail(id: number) {
    if (detailId === id) { setDetailId(null); return }
    setDetailId(id); setDetailData(null); setLoadingDetail(true)
    try {
      const data = await api.fetchHistoryDetail(id)
      setDetailData(data)
    } catch (e) { console.error(e) } finally { setLoadingDetail(false) }
  }

  async function handleDelete(id: number, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm('确定删除这条搜索记录？')) return
    try {
      await api.deleteHistoryRecord(id)
      loadHistory()
      if (detailId === id) { setDetailId(null); setDetailData(null) }
    } catch (e: any) { alert(e.message || '删除失败') }
  }

  async function handleClearAll() {
    if (!confirm(`确定清空全部 ${total} 条记录？不可恢复。`)) return
    try {
      await api.clearAllHistory()
      setRecords([]); setTotal(0); setDetailId(null); setDetailData(null)
    } catch (e: any) { alert(e.message || '清空失败') }
  }

  function fmtTime(s: string): string {
    try { return new Date(s).toLocaleString('zh-CN', { hour12: false }) } catch { return s }
  }

  // ── 渲染 ───────────────────────────────────────────────
  return (
    <div className="page-container" style={{ maxWidth: '1100px', paddingTop: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700,
            background: 'linear-gradient(135deg, #4AFF91, #00D4FF)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>SEARCH HISTORY</h2>
          <p style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '13px' }}>
            共 {total} 条记录 &mdash; 持久化存储，重启不丢失
          </p>
        </div>
        {total > 0 && (
          <button onClick={handleClearAll} style={{
            background: 'rgba(255,82,82,.08)', border: '1px solid rgba(255,82,82,.25)',
            color: '#ff5252', borderRadius: '8px', padding: '7px 18px',
            fontSize: '12px', cursor: 'pointer', fontFamily: 'inherit', transition: '.2s',
          }}>{'\uD83D\uDDD1'} Clear All</button>
        )}
      </div>

      {loading && (
        <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '60px 0', fontSize: '14px' }}>
          Loading history...
        </p>
      )}
      {!loading && records.length === 0 && (
        <div className="glass-card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <span style={{ fontSize: '48px' }}>{'\uD83D\uDCC4'}</span>
          <p style={{ color: 'var(--text-secondary)', fontSize: '15px', marginTop: '16px' }}>
            No search history yet
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '8px' }}>
            搜索导师后，结果将自动保存在此处
          </p>
          <button onClick={() => navigate('/')} style={{
            marginTop: '20px', background: 'rgba(0,212,255,.1)', border: '1px solid rgba(0,212,255,.3)',
            color: '#00D4FF', borderRadius: '10px', padding: '9px 28px',
            fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit',
          }}>{'\u27A4'} Go Search</button>
        </div>
      )}

      {!loading && records.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: detailId ? '1fr 420px' : '1fr', gap: '20px', alignItems: 'start' }}>
          {/* ─── 左侧：列表 ─── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {records.map(rec => (
              <div key={rec.id}
                onClick={() => loadDetail(rec.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '14px',
                  padding: '16px 20px', borderRadius: '12px', cursor: 'pointer',
                  transition: 'all .2s',
                  background: detailId === rec.id ? 'rgba(0,212,255,.08)' : 'transparent',
                  border: `1px solid ${detailId === rec.id ? 'rgba(0,212,255,.3)' : 'var(--border-color)'}`,
                }}
                onMouseEnter={e => {
                  if (detailId !== rec.id) {
                    e.currentTarget.style.borderColor = 'rgba(0,212,255,.2)'
                    e.currentTarget.style.background = 'rgba(0,212,255,.04)'
                  }
                }}
                onMouseLeave={e => {
                  if (detailId !== rec.id) {
                    e.currentTarget.style.borderColor = 'var(--border-color)'
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <div style={{
                  width: '40px', height: '40px', borderRadius: '10px',
                  background: 'rgba(74,255,145,.08)', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px',
                }}>{'\uD83D\uDD0D'}</div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#E8EDF5',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {rec.query || '(empty query)'}
                  </div>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '5px', fontSize: '11px', color: 'var(--text-muted)' }}>
                    <span>{'\uD83D\uDD52'} {fmtTime(rec.created_at)}</span>
                    {rec.university && <span>{'\uD83C\uDFDB'} {rec.university}</span>}
                    {/* platforms_used 安全解析 */}
                    {(() => {
                      const p = parsePlatforms(rec.platforms_used)
                      return p.length > 0 ? <span>{'\uD83C\uDF10'} {p.join(', ')}</span> : null
                    })()}
                  </div>
                </div>

                <div style={{
                  padding: '4px 12px', borderRadius: '8px',
                  background: rec.total_count > 0 ? 'rgba(74,255,145,.08)' : 'rgba(255,176,32,.06)',
                  color: rec.total_count > 0 ? '#4AFF91' : '#FFB020',
                  fontSize: '13px', fontWeight: 700, whiteSpace: 'nowrap',
                }}>{rec.total_count} reviews</div>

                <div style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                  {rec.elapsed_seconds}s
                </div>

                {/* 删除按钮 — 始终可见 */}
                <button onClick={(e) => handleDelete(rec.id, e)}
                  title="删除此记录"
                  style={{
                    background: 'none', border: '1px solid transparent',
                    color: 'var(--text-muted)', cursor: 'pointer',
                    fontSize: '14px', padding: '4px 6px', borderRadius: '4px',
                    transition: '.2s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.color = '#ff5252'
                    e.currentTarget.style.borderColor = 'rgba(255,82,82,.3)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.color = 'var(--text-muted)'
                    e.currentTarget.style.borderColor = 'transparent'
                  }}
                >{'\u2715'}</button>
              </div>
            ))}
          </div>

          {/* ─── 右侧：详情面板 ─── */}
          {detailId !== null && (
            <div className="glass-card" style={{
              position: 'sticky', top: '100px',
              padding: '24px', maxHeight: '80vh', overflowY: 'auto',
            }}>
              {loadingDetail ? (
                <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px 0' }}>Loading...</p>
              ) : detailData ? (
                <HistoryDetailView data={detailData} onClose={() => setDetailId(null)} />
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── 详情视图 ─────────────────────────────────────────
function HistoryDetailView({ data, onClose }: { data: api.HistoryDetail; onClose: () => void }) {
  const navigate = useNavigate()
  const totalReviews = data.results.reduce((sum, r) => sum + r.reviews.length, 0)
  const scoredResults = data.results.filter(r => r.overall_score != null)
  const avgScore = scoredResults.length > 0
    ? scoredResults.reduce((sum, r) => sum + (r.overall_score ?? 0), 0) / scoredResults.length
    : null
  // 好评率：评分 >= 7 的结果占比
  const positiveCount = scoredResults.filter(r => (r.overall_score ?? 0) >= 7).length
  const positiveRate = scoredResults.length > 0
    ? Math.round((positiveCount / scoredResults.length) * 100)
    : null

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '18px' }}>
        <div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#E8EDF5' }}>{data.query}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {new Date(data.created_at).toLocaleString('zh-CN', { hour12: false })}
          </div>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: '1px solid var(--border-color)',
          color: 'var(--text-muted)', borderRadius: '6px',
          width: '28px', height: '28px', cursor: 'pointer', fontSize: '14px',
        }}>{'\u2715'}</button>
      </div>

      {/* 一键跳转分析 — 带完整评论数据 */}
      {totalReviews > 0 && (
        <div style={{ marginBottom: '16px' }}>
          {data.results.map((r, i) => r.reviews.length > 0 ? (
            <button key={i} onClick={() => navigate('/analysis', { state: { result: r } })}
              style={{
                width: '100%', padding: '10px 16px', borderRadius: '10px',
                background: 'linear-gradient(135deg, rgba(176,136,249,.12), rgba(0,212,255,.06))',
                border: '1px solid rgba(176,136,249,.25)', cursor: 'pointer',
                color: '#B088F9', fontSize: '13px', fontWeight: 600,
                fontFamily: 'inherit', transition: '.2s',
                marginBottom: i < data.results.length - 1 ? '6px' : 0,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(176,136,249,.5)'; e.currentTarget.style.background = 'linear-gradient(135deg, rgba(176,136,249,.18), rgba(0,212,255,.1))' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(176,136,249,.25)'; e.currentTarget.style.background = 'linear-gradient(135deg, rgba(176,136,249,.12), rgba(0,212,255,.06))' }}
            >
              {'\uD83D\uDD0D'} Analyze {r.name} ({r.reviews.length} reviews) →
            </button>
          ) : null)}
        </div>
      )}

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '18px' }}>
        {[
          { label: 'Reviews', value: String(totalReviews), icon: '\uD83D\uDCDD', color: '#4AFF91' },
          { label: 'Positive', value: positiveRate != null ? `${positiveRate}%` : '-', icon: '\uD83D\uDC4D', color: '#00D4FF' },
          { label: 'Sources', value: String(data.platforms_used?.length ?? 0), icon: '\uD83C\uDF10', color: '#B088F9' },
          { label: 'Avg Score', value: avgScore ? avgScore.toFixed(1) : '-', icon: '\u2B50', color: '#FFB020' },
        ].map(item => (
          <div key={item.label} style={{
            background: `${item.color}08`, border: `1px solid ${item.color}20`,
            borderRadius: '10px', padding: '12px', textAlign: 'center',
          }}>
            <div style={{ fontSize: '18px' }}>{item.icon}</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: item.color, margin: '4px 0' }}>{item.value}</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>{item.label}</div>
          </div>
        ))}
      </div>

      {/* 来源平台 */}
      {(data.platforms_used?.length ?? 0) > 0 && (
        <div style={{ marginBottom: '18px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '1px' }}>SOURCES</div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {(Array.isArray(data.platforms_used) ? data.platforms_used : []).map((p: string) => (
              <span key={p} style={{
                background: 'rgba(0,212,255,.1)', border: '1px solid rgba(0,212,255,.2)',
                color: '#00D4FF', borderRadius: '6px', padding: '3px 10px',
                fontSize: '11px', fontWeight: 600,
              }}>{p}</span>
            ))}
          </div>
        </div>
      )}

      {/* 结果卡片 — 每条含 Source Link */}
      {data.results.length > 0 && (
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '1px' }}>
            RESULTS ({data.results.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {data.results.map((r, i) => (
              <div key={i} style={{
                background: 'rgba(0,0,0,.2)', borderRadius: '8px',
                padding: '10px 14px', border: '1px solid var(--border-color)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#E8EDF5' }}>{r.name}</div>
                  {r.overall_score != null && (
                    <span style={{
                      fontSize: '12px', fontWeight: 700, color: '#FFB020',
                      background: 'rgba(255,176,32,.1)', padding: '1px 8px', borderRadius: '4px',
                    }}>{r.overall_score.toFixed(1)}</span>
                  )}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {[r.university, r.department].filter(Boolean).join(' · ')}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px', fontSize: '11px' }}>
                  <span style={{ color: '#4AFF91' }}>{r.review_count} reviews</span>
                  <span style={{ color: 'var(--text-muted)' }}>{r.source}</span>
                  {/* Source Link */}
                  {r.detail_url && (
                    <a href={fullUrl(r.detail_url)} target="_blank" rel="noreferrer"
                      style={{
                        color: '#00D4FF', textDecoration: 'none', marginLeft: 'auto',
                        borderBottom: '1px dotted rgba(0,212,255,.3)',
                        transition: '.2s',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.color = '#4AFF91' }}
                      onMouseLeave={e => { e.currentTarget.style.color = '#00D4FF' }}
                    >{'\uD83D\uDD17'} Source Link</a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
