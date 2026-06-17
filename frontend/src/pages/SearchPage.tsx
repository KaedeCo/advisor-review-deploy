import { useState, useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { Button, MessagePlugin, Loading, Tag } from 'tdesign-react'
import PlatformSelector from '../components/PlatformSelector'
import ResultCards from '../components/ResultCards'
import { useNavigate, Link } from 'react-router-dom'
import * as api from '../services/api'

/**
 * 搜索页 — 平台选择 + 激光炮按钮 + 结果展示
 */
export default function SearchPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [university, setUniversity] = useState('')
  const [department, setDepartment] = useState('')

  const [platforms, setPlatforms] = useState<api.Platform[]>([])
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])

  const [results, setResults] = useState<api.AdvisorResult[]>([])
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (location.state) {
      const s = location.state as Record<string, string>
      setName(s.name || '')
      setUniversity(s.university || '')
      setDepartment(s.department || '')
    }
    fetchPlatforms()
  }, [])

  async function fetchPlatforms() {
    try {
      const data = await api.fetchPlatforms()
      const list: api.Platform[] = Object.entries(data).map(([key, val]) => ({
        key,
        name: (val as unknown as api.Platform).name,
        enabled: (val as unknown as api.Platform).enabled,
        tier: (val as unknown as api.Platform).tier,
      }))
      setPlatforms(list)
      setSelectedKeys(list.filter(p => p.enabled).map(p => p.key))
    } catch (e) {
      console.error('获取平台失败', e)
    }
  }

  /** IMMA CHARGIN MAH LAZER!!! */
  const handleSearch = useCallback(async () => {
    if (!name.trim()) {
      MessagePlugin.warning('请输入导师姓名')
      return
    }
    if (!selectedKeys.length) {
      MessagePlugin.warning('请至少勾选一个平台')
      return
    }

    setLoading(true)
    setResults([])
    try {
      const res = await api.searchAdvisor({
        advisor_name: name.trim(),
        university: university.trim(),
        department: department.trim(),
        platforms: selectedKeys,
      })
      setResults(res.results)
      setElapsed(res.elapsed_seconds)
      if (res.results.length > 0) {
        await MessagePlugin.success(`扫描完成！捕获 ${res.total_count} 条数据 · 耗时 ${res.elapsed_seconds}s`)
      } else {
        await MessagePlugin.info('未检测到相关信号，建议更换关键词或启用更多数据源')
      }
    } catch (err: any) {
      await MessagePlugin.error(err.message || '搜索请求失败，请检查后端连接')
    } finally {
      setLoading(false)
    }
  }, [name, university, department, selectedKeys])

  const handleAnalyze = (result: api.AdvisorResult) => {
    navigate('/analysis', { state: { result } })
  }

  return (
    <div className="page-container" style={{ paddingTop: '8px' }}>
      {/* 目标信息栏 */}
      <div className="glass-card" style={{
        padding: '18px 28px',
        marginBottom: '24px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>TARGET:</span>
          <span style={{
            fontSize: '20px', fontWeight: 700,
            background: 'linear-gradient(135deg, #00D4FF, #4AFF91)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            {name || '(未指定)'}
          </span>
          {[university, department].filter(Boolean).length > 0 && (
            <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              / {[university, department].filter(Boolean).join(' / ')}
            </span>
          )}
          {results.length > 0 && (
            <Tag variant="light-outline" theme="success"
              style={{ borderColor: '#4AFF91', color: '#4AFF91' }}
            >
              {results.length} results | {elapsed}s
            </Tag>
          )}
        </div>
        <Link to="/" style={{ textDecoration: 'none' }}>
          <Button variant="outline" size="small">← HOME</Button>
        </Link>
      </div>

      {/* 数据源选择 + 发射面板 */}
      <div className="glass-card scanline" style={{ padding: '28px 32px', marginBottom: '28px' }}>
        {/* 标题栏 */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '16px',
        }}>
          <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '15px', fontWeight: 600, letterSpacing: '1px' }}>
            DATA SOURCE CONFIG
          </h3>
          <Tag variant="light" size="small"
            style={{ background: 'rgba(0,212,255,.08)', color: '#00D4FF', border: 'none' }}
          >
            {selectedKeys.length} / {platforms.length} ACTIVE
          </Tag>
        </div>

        <PlatformSelector platforms={platforms} selectedKeys={selectedKeys} onChange={setSelectedKeys} />

        {/* 激光按钮 */}
        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <Button
            size="large"
            loading={loading}
            onClick={handleSearch}
            className="laser-btn"
            style={{
              minWidth: '380px', height: '56px',
              fontSize: '17px', fontWeight: 900,
              letterSpacing: '2.5px', textTransform: 'uppercase',
              background: loading ? undefined : 'linear-gradient(135deg, #FF6B35, #FF8F35)',
              border: 'none', borderRadius: '14px',
              fontFamily: '"Courier New", monospace',
              boxShadow: '0 4px 30px rgba(255,107,53,.25), inset 0 1px 0 rgba(255,255,255,.12)',
              transition: 'all .3s',
              color: '#FFF',
            }}
          >
            {loading ? 'SCANNING...' : 'IMMA CHARGIN MAH LAZER!!!'}
          </Button>
        </div>
      </div>

      {/* 搜索结果 */}
      {loading ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '48px' }}>
          <Loading text="正在从各数据源采集信息..." />
        </div>
      ) : results.length > 0 ? (
        <ResultCards results={results} onAnalyze={handleAnalyze} />
      ) : null}
    </div>
  )
}
