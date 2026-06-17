import { useState, useEffect } from 'react'
import * as api from '../services/api'

/**
 * KPI 监控侧边栏 — 可展开/收起的左侧浮动面板
 */
export default function KpiSidebar() {
  const [open, setOpen] = useState(false)
  const [stats, setStats] = useState<api.KpiStats | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open && !stats) {
      loadStats()
    }
  }, [open])

  // 定时刷新（打开时每 30 秒）
  useEffect(() => {
    if (!open) return
    const timer = setInterval(loadStats, 30000)
    return () => clearInterval(timer)
  }, [open])

  async function loadStats() {
    setLoading(true)
    try {
      const data = await api.fetchKpiStats()
      setStats(data)
    } catch { /* 静默 */ }
    finally { setLoading(false) }
  }

  return (
    <>
      {/* 展开/收起按钮 */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          position: 'fixed',
          left: open ? '280px' : '0',
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 200,
          width: '24px',
          height: '60px',
          borderRadius: '0 8px 8px 0',
          border: '1px solid rgba(0,212,255,.2)',
          borderLeft: 'none',
          background: 'rgba(10,14,23,.9)',
          backdropFilter: 'blur(20px)',
          color: '#00D4FF',
          cursor: 'pointer',
          fontFamily: 'inherit',
          fontSize: '14px',
          transition: 'left .25s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        title={open ? '收起 KPI' : '展开 KPI'}
      >
        {open ? '\u2039' : '\u203A'}
      </button>

      {/* 侧边栏面板 */}
      {open && (
        <div style={{
          position: 'fixed',
          left: '0',
          top: '64px',
          bottom: '0',
          width: '280px',
          zIndex: 199,
          background: 'rgba(10,14,23,.95)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(0,212,255,.1)',
          overflowY: 'auto',
          padding: '20px 16px',
          animation: 'slideInLeft .25s ease-out',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: '20px',
          }}>
            <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '14px', fontWeight: 700, letterSpacing: '1px' }}>
              KPI DASHBOARD
            </h4>
            <button
              onClick={loadStats}
              disabled={loading}
              style={{
                background: 'rgba(0,212,255,.08)', border: '1px solid rgba(0,212,255,.2)',
                borderRadius: '6px', color: '#00D4FF', fontSize: '11px',
                cursor: loading ? 'wait' : 'pointer', padding: '3px 10px',
                fontFamily: 'inherit',
              }}
            >
              {loading ? '...' : 'Refresh'}
            </button>
          </div>

          {stats ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* 数据覆盖 */}
              <KpiSection title="Data Coverage" color="#4AFF91">
                <KpiItem label="GitHub Advisors" value={stats.github_advisors.toLocaleString()} />
                <KpiItem label="GitHub Reviews" value={stats.github_reviews.toLocaleString()} />
                <KpiItem label="Advisors Analyzed" value={stats.unique_advisors_analyzed.toString()} />
                <KpiItem label="Reviews Analyzed" value={stats.total_reviews_analyzed.toLocaleString()} />
              </KpiSection>

              {/* 搜索性能 */}
              <KpiSection title="Search Performance" color="#00D4FF">
                <KpiItem label="Total Searches" value={stats.total_searches.toString()} />
                <KpiItem label="Avg Latency" value={`${stats.avg_search_latency}s`} />
                <KpiItem label="Results Returned" value={stats.total_results_returned.toLocaleString()} />
                {stats.latest_search && (
                  <KpiItem label="Last Search" value={formatTime(stats.latest_search)} small />
                )}
              </KpiSection>

              {/* AI 分析 */}
              <KpiSection title="AI Analysis" color="#B088F9">
                <KpiItem label="Total Analyses" value={stats.total_analyses.toString()} />
                <KpiItem label="SnowNLP Calls" value={stats.snownlp_calls.toString()} />
                <KpiItem label="DeepSeek Calls" value={stats.deepseek_calls.toString()} />
                <KpiItem label="6D Scoring Runs" value={stats.dim_score_calls.toString()} />
                {stats.latest_analysis && (
                  <KpiItem label="Last Analysis" value={formatTime(stats.latest_analysis)} small />
                )}
              </KpiSection>

              {/* 平台状态 */}
              <KpiSection title="Data Sources" color="#FFD54F">
                <KpiItem
                  label="Active Platforms"
                  value={`${stats.enabled_platforms}/${stats.total_platforms}`}
                />
                <KpiItem
                  label="DeepSeek"
                  value={stats.deepseek_configured ? 'Configured' : 'Not Set'}
                  color={stats.deepseek_configured ? '#4AFF91' : '#FF6B35'}
                />
                <KpiItem
                  label="Tavily"
                  value={stats.tavily_configured ? 'Configured' : 'Not Set'}
                  color={stats.tavily_configured ? '#4AFF91' : '#FF6B35'}
                />
              </KpiSection>

              {/* 平台使用频率 */}
              {Object.keys(stats.platform_frequency).length > 0 && (
                <KpiSection title="Platform Usage" color="#4A9EFF">
                  {Object.entries(stats.platform_frequency)
                    .sort((a, b) => b[1] - a[1])
                    .map(([key, count]) => (
                      <div key={key} style={{ marginBottom: '6px' }}>
                        <div style={{
                          display: 'flex', justifyContent: 'space-between',
                          fontSize: '11px', marginBottom: '2px',
                        }}>
                          <span style={{ color: 'var(--text-secondary)' }}>{key}</span>
                          <span style={{ color: '#4A9EFF', fontWeight: 600 }}>{count}</span>
                        </div>
                        <div style={{
                          height: '3px', borderRadius: '2px',
                          background: 'rgba(74,158,255,.1)',
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${(count / Math.max(...Object.values(stats.platform_frequency))) * 100}%`,
                            background: 'linear-gradient(90deg, #4A9EFF, #00D4FF)',
                            borderRadius: '2px',
                            transition: 'width .3s',
                          }} />
                        </div>
                      </div>
                    ))}
                </KpiSection>
              )}
            </div>
          ) : loading ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center', padding: '20px' }}>
              Loading...
            </p>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center', padding: '20px' }}>
              Failed to load stats
            </p>
          )}
        </div>
      )}
    </>
  )
}

function KpiSection({ title, color, children }: {
  title: string
  color: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div style={{
        fontSize: '10px', color, fontWeight: 700,
        letterSpacing: '1px', textTransform: 'uppercase',
        marginBottom: '8px', paddingLeft: '2px',
      }}>
        // {title}
      </div>
      <div style={{
        background: 'rgba(255,255,255,.02)',
        borderRadius: '8px',
        padding: '10px 12px',
        border: '1px solid rgba(255,255,255,.04)',
      }}>
        {children}
      </div>
    </div>
  )
}

function KpiItem({ label, value, color, small }: {
  label: string
  value: string
  color?: string
  small?: boolean
}) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: small ? '2px 0' : '4px 0',
    }}>
      <span style={{
        fontSize: small ? '10px' : '11px',
        color: 'var(--text-muted)',
      }}>
        {label}
      </span>
      <span style={{
        fontSize: small ? '10px' : '13px',
        fontWeight: 600,
        color: color || '#E8EDF5',
      }}>
        {value}
      </span>
    </div>
  )
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diff = (now.getTime() - d.getTime()) / 1000
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return iso
  }
}
