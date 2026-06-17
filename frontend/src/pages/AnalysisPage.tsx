import { useState, useEffect, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button, Tag, Space, MessagePlugin, Loading, Alert } from 'tdesign-react'
import { Link } from 'react-router-dom'
import SentimentChart from '../components/SentimentChart'
import RadarChart from '../components/RadarChart'
import * as api from '../services/api'

function fullUrl(path: string) {
  if (!path) return ''
  return path.startsWith('http') ? path : `https://gradchoice.org${path}`
}

/**
 * 分析页 — SnowNLP + DeepSeek Sentiment + DeepSeek 综合 + 六维雷达评分 四引擎
 */
export default function AnalysisPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const [result, setResult] = useState<api.AdvisorResult | null>(null)
  const [sentiment, setSentiment] = useState<api.SentimentResult | null>(null)
  const [sentimentLoading, setSentimentLoading] = useState(false)
  const [dsSentiment, setDsSentiment] = useState<api.SentimentResult | null>(null)
  const [dsSentimentLoading, setDsSentimentLoading] = useState(false)
  const [dsSentimentError, setDsSentimentError] = useState<string>('')
  const [deepseekData, setDeepseekData] = useState<api.DeepseekResponse | null>(null)
  const [deepseekLoading, setDeepseekLoading] = useState(false)
  const [deepseekError, setDeepseekError] = useState<string>('')
  const [dimScores, setDimScores] = useState<api.DimensionScores | null>(null)
  const [dimLoading, setDimLoading] = useState(false)
  const [dimError, setDimError] = useState<string>('')
  const [redFlagsSummary, setRedFlagsSummary] = useState<string[]>([])
  const [sentimentTab, setSentimentTab] = useState<'snownlp' | 'deepseek'>('snownlp')

  useEffect(() => {
    if (location.state?.result) {
      setResult(location.state.result as api.AdvisorResult)
    }
  }, [])

  // 导师数据加载后，尝试从数据库恢复已保存的分析结果
  useEffect(() => {
    if (!result?.name) return
    loadSavedAnalysis(result.name)
  }, [result?.name])

  useEffect(() => {
    if (result?.reviews?.length && !sentiment) {
      handleSnowNLPAnalyze()
    }
  }, [result, sentiment])

  /** 从数据库加载已保存的分析结果 */
  async function loadSavedAnalysis(advisorName: string) {
    try {
      const list = await api.fetchAnalysisList()
      const match = list.records.find(
        r => r.advisor_name === advisorName
      )
      if (match) {
        // 加载完整数据（含附件）
        const detail = await api.fetchAnalysisDetail(match.id)
        if (detail.sentiment) {
          setSentiment(detail.sentiment)
        }
        if ((detail as any).deepseek_sentiment) {
          setDsSentiment((detail as any).deepseek_sentiment)
        }
        if (detail.deepseek) {
          setDeepseekData(detail.deepseek)
        }
        if ((detail as any).dimension_scores) {
          setDimScores((detail as any).dimension_scores)
        }
      }
    } catch { /* 静默 */ }
  }

  const reviewsText = useMemo(
    () => result?.reviews?.map(r => `[${r.author || 'anonymous'}] ${r.content}`).join('\n\n') || '',
    [result]
  )

  async function handleSnowNLPAnalyze() {
    if (!reviewsText) return
    setSentimentLoading(true)
    try {
      const data = await api.analyzeSentiment(reviewsText, {
        name: result?.name,
        university: result?.university,
        department: result?.department,
        reviewCount: result?.reviews?.length ?? 0,
      })
      setSentiment(data)
    } catch (e: any) {
      await MessagePlugin.error('SnowNLP analysis failed: ' + e.message)
    } finally {
      setSentimentLoading(false)
    }
  }

  async function handleDSentimentAnalyze() {
    if (!reviewsText) return
    setDsSentimentLoading(true)
    setDsSentimentError('')
    try {
      const data = await api.analyzeSentimentDeepseek(reviewsText, {
        name: result?.name,
        university: result?.university,
        department: result?.department,
        reviewCount: result?.reviews?.length ?? 0,
      })
      setDsSentiment(data)
      setSentimentTab('deepseek')
      await MessagePlugin.success(`DeepSeek 评估完成 · 共 ${data.total_count} 条`)
    } catch (e: any) {
      setDsSentimentError(e.message || 'DeepSeek 情感分类失败')
      await MessagePlugin.error(e.message || 'DeepSeek 情感分类失败')
    } finally {
      setDsSentimentLoading(false)
    }
  }

  async function handleDeepSeekAnalyze() {
    if (!reviewsText) return
    setDeepseekLoading(true)
    setDeepseekError('')
    try {
      const data = await api.analyzeDeepseek(reviewsText, {
        name: result?.name,
        university: result?.university,
        department: result?.department,
        reviewCount: result?.reviews?.length ?? 0,
      })
      setDeepseekData(data)
      await MessagePlugin.success('DeepSeek analysis saved to database')
    } catch (e: any) {
      setDeepseekError(e.message || 'DeepSeek API failed.')
      await MessagePlugin.error(e.message || 'DeepSeek API failed.')
    } finally {
      setDeepseekLoading(false)
    }
  }

  async function handleDimensionAnalyze() {
    if (!reviewsText) return
    setDimLoading(true)
    setDimError('')
    try {
      const data = await api.analyzeDimensions(reviewsText, {
        name: result?.name,
        university: result?.university,
        department: result?.department,
        reviewCount: result?.reviews?.length ?? 0,
      })
      setDimScores(data.scores)
      setRedFlagsSummary(data.red_flags_summary || [])
      await MessagePlugin.success(
        `六维评分完成 · 综合分 ${data.scores.overall} · ${data.saved ? '已落盘' : '未持久化'}`
      )
    } catch (e: any) {
      setDimError(e.message || '六维评分失败.')
      await MessagePlugin.error(e.message || '六维评分失败.')
    } finally {
      setDimLoading(false)
    }
  }

  // 空状态
  if (!result) {
    return (
      <div className="page-container" style={{ textAlign: 'center', paddingTop: '80px' }}>
        <Alert theme="warning" message="No data received. Please search for an advisor first." />
        <br />
        <Link to="/">
          <Button variant="outline">← BACK TO SEARCH</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* 导师信息头 */}
      <div className="glass-card scanline" style={{
        padding: '24px 32px',
        marginBottom: '24px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '20px' }}>
            <span style={{
              background: 'linear-gradient(135deg, #00D4FF, #4AFF91)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>{result.name}</span>
          </h3>
          <div style={{ marginTop: '8px', color: 'var(--text-secondary)', fontSize: '14px' }}>
            {[result.university, result.department].filter(Boolean).join(' · ') || ''}
            <span style={{ margin: '0 12px', color: 'rgba(100,130,180,.3)' }}>|</span>
            Source: <Tag variant="light" size="small">{result.source}</Tag>
            <span style={{ margin: '0 12px', color: 'rgba(100,130,180,.3)' }}>|</span>
            {result.reviews.length} reviews
          </div>
        </div>
        <Link to="/search">
          <Button variant="outline" size="small">← RESULTS</Button>
        </Link>
      </div>

      {/* ====== 全部评论浏览区 ====== */}
      <ReviewBrowser reviews={result.reviews} />

      {/* ====== Sentiment Analysis（Tab 切换）====== */}
      <div className="glass-card" style={{ padding: '28px 32px', marginBottom: '24px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '20px', flexWrap: 'wrap', gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '18px' }}>{'\uD83D\uDCCA'}</span>
            <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '16px', fontWeight: 600 }}>
              Sentiment Analysis
            </h4>
          </div>
          <Button
            theme="primary"
            variant="outline"
            size="small"
            loading={dsSentimentLoading}
            onClick={handleDSentimentAnalyze}
            disabled={!result?.reviews?.length}
            style={{ borderColor: 'rgba(176,136,249,.5)', color: '#B088F9' }}
          >
            {dsSentimentLoading ? 'DeepSeek analyzing...' : 'Re-analyze with DeepSeek'}
          </Button>
        </div>

        {(!result.reviews?.length) && (
          <div style={{
            padding: '20px', textAlign: 'center', color: 'var(--text-muted)',
            fontSize: '13px',
          }}>
            <p>No review content available for analysis.</p>
          </div>
        )}

        {dsSentimentError && (
          <Alert theme="error" message={dsSentimentError} style={{ marginBottom: '16px' }} />
        )}

        {sentimentLoading ? (
          <Loading text="SnowNLP analyzing..." />
        ) : sentiment ? (
          <>
            {/* Tabs */}
            <div style={{
              display: 'flex', gap: '0', marginBottom: '16px',
              borderBottom: '1px solid rgba(100,130,180,.12)',
            }}>
              <button
                onClick={() => setSentimentTab('snownlp')}
                style={{
                  background: 'none', border: 'none',
                  padding: '10px 20px',
                  fontSize: '13px', fontWeight: sentimentTab === 'snownlp' ? 600 : 400,
                  color: sentimentTab === 'snownlp' ? '#4AFF91' : 'var(--text-muted)',
                  borderBottom: sentimentTab === 'snownlp'
                    ? '2px solid #4AFF91' : '2px solid transparent',
                  cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'all .2s',
                }}
              >
                <Tag variant="light" size="small"
                  style={{
                    background: 'rgba(74,255,145,.1)', color: '#4AFF91', border: 'none',
                    marginRight: '8px',
                  }}
                >SnowNLP</Tag>
                {sentiment.total_count} reviews
              </button>
              {dsSentiment && (
                <button
                  onClick={() => setSentimentTab('deepseek')}
                  style={{
                    background: 'none', border: 'none',
                    padding: '10px 20px',
                    fontSize: '13px', fontWeight: sentimentTab === 'deepseek' ? 600 : 400,
                    color: sentimentTab === 'deepseek' ? '#B088F9' : 'var(--text-muted)',
                    borderBottom: sentimentTab === 'deepseek'
                      ? '2px solid #B088F9' : '2px solid transparent',
                    cursor: 'pointer', fontFamily: 'inherit',
                    transition: 'all .2s',
                  }}
                >
                  <Tag variant="light" size="small"
                    style={{
                      background: 'rgba(176,136,249,.1)', color: '#B088F9', border: 'none',
                      marginRight: '8px',
                    }}
                  >DeepSeek</Tag>
                  {dsSentiment.total_count} reviews
                </button>
              )}
            </div>

            {/* Tab 内容 */}
            {sentimentTab === 'snownlp' ? (
              <>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '12px', fontSize: '13px' }}>
                  Local NLP model. Score &gt;0.6 = Positive, &lt;0.4 = Negative, 0.4~0.6 = Neutral.
                </p>
                <SentimentChart data={sentiment} />
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '-8px' }}>
                  <StatBadge label="POSITIVE" value={sentiment.positive_count} theme="#4AFF91" />
                  <StatBadge label="NEUTRAL" value={sentiment.neutral_count} theme="#4A9EFF" />
                  <StatBadge label="NEGATIVE" value={sentiment.negative_count} theme="#FF6B35" />
                </div>
              </>
            ) : dsSentiment ? (
              <>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '12px', fontSize: '13px' }}>
                  DeepSeek LLM classifies each review individually.
                </p>
                <SentimentChart data={dsSentiment} />
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '-8px' }}>
                  <StatBadge label="POSITIVE" value={dsSentiment.positive_count} theme="#B088F9" />
                  <StatBadge label="NEUTRAL" value={dsSentiment.neutral_count} theme="#4A9EFF" />
                  <StatBadge label="NEGATIVE" value={dsSentiment.negative_count} theme="#FF6B35" />
                </div>
              </>
            ) : null}
          </>
        ) : null}
      </div>

      {/* ====== DeepSeek 深度分析 ====== */}
      <div className="glass-card" style={{ padding: '28px 32px', marginBottom: '28px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '20px', flexWrap: 'wrap', gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '18px' }}>🤖</span>
            <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '16px', fontWeight: 600 }}>
              DeepSeek AI Deep Analysis
            </h4>
            <Tag variant="light" size="small"
              style={{ background: 'rgba(176,136,249,.1)', color: '#B088F9', border: 'none' }}
            >CLOUD LLM</Tag>
          </div>
          <Button
            theme="primary"
            variant="outline"
            size="large"
            loading={deepseekLoading}
            onClick={handleDeepSeekAnalyze}
            style={{ borderColor: 'rgba(176,136,249,.5)', color: '#B088F9' }}
          >
            {deepseekLoading ? 'AI Thinking...' : 'Invoke DeepSeek'}
          </Button>
        </div>

        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '13px' }}>
          Leverage DeepSeek LLM to extract pros/cons, risk flags &amp; overall rating.
        </p>

        {deepseekError && (
          <Alert theme="error" message={deepseekError} style={{ marginBottom: '16px' }} />
        )}

        {deepseekLoading && <Loading text="DeepSeek processing..." />}

        {deepseekData && !deepseekLoading && (
          <div style={{ animation: 'fadeInUp .4s ease-out both' }}>
            {/* 综合评分 */}
            {deepseekData.overall_rating != null && (
              <div style={{
                textAlign: 'center', padding: '28px', marginBottom: '24px',
                borderRadius: '14px',
                background: deepseekData.overall_rating! >= 7
                  ? 'linear-gradient(135deg, rgba(74,255,145,.06), rgba(74,255,145,.02))'
                  : deepseekData.overall_rating! >= 5
                    ? 'linear-gradient(135deg, rgba(255,200,50,.06), rgba(255,200,50,.02))'
                    : 'linear-gradient(135deg, rgba(255,107,53,.08), rgba(255,107,53,.02))',
                border: `1px solid ${deepseekData.overall_rating! >= 7 ? 'rgba(74,255,145,.15)' : deepseekData.overall_rating! >= 5 ? 'rgba(255,200,50,.15)' : 'rgba(255,107,53,.15)'}`,
              }}>
                <div style={{ fontSize: '56px', fontWeight: 900, lineHeight: 1,
                  color: deepseekData.overall_rating! >= 7 ? '#4AFF91' : deepseekData.overall_rating! >= 5 ? '#FFD54F' : '#FF6B35',
                }}>
                  {deepseekData.overall_rating}
                  <span style={{ fontSize: '20px', color: 'var(--text-muted)' }}>/10</span>
                </div>
                <div style={{ color: 'var(--text-secondary)', marginTop: '4px', letterSpacing: '2px', fontSize: '13px' }}>
                  DEEPSEEK OVERALL RATING
                </div>
              </div>
            )}

            {/* 摘要 */}
            {deepseekData.summary && (
              <div className="glass-card" style={{ padding: '22px 28px', marginBottom: '20px' }}>
                <h5 style={{
                  margin: '0 0 10px', color: '#00D4FF', fontSize: '13px',
                  letterSpacing: '1px', textTransform: 'uppercase',
                }}>// Summary</h5>
                <p style={{ lineHeight: 1.85, whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', fontSize: '14px' }}>
                  {deepseekData.summary}
                </p>
              </div>
            )}

            {/* 优点 / 缺点 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {/* Pros */}
              <div className="glass-card" style={{ padding: '22px 24px' }}>
                <h5 style={{ margin: '0 0 14px', color: '#4AFF91', fontSize: '14px', fontWeight: 700 }}>
                  ✅ PROS ({deepseekData.pros.length})
                </h5>
                {deepseekData.pros.map((p, i) => (
                  <div key={i} style={{
                    padding: '10px 0',
                    borderBottom: i < deepseekData.pros.length - 1 ? '1px solid rgba(74,255,145,.1)' : 'none',
                    fontSize: '14px', color: 'var(--text-secondary)',
                  }}>
                    <Tag size="small" theme="success" variant="outline" style={{ marginRight: '8px', borderColor: '#4AFF91', color: '#4AFF91' }}>PRO</Tag>{p}
                  </div>
                ))}
              </div>

              {/* Cons */}
              <div className="glass-card" style={{ padding: '22px 24px' }}>
                <h5 style={{ margin: '0 0 14px', color: '#FF6B35', fontSize: '14px', fontWeight: 700 }}>
                  ⚠️ CONS ({deepseekData.cons.length})
                </h5>
                {deepseekData.cons.map((c, i) => (
                  <div key={i} style={{
                    padding: '10px 0',
                    borderBottom: i < deepseekData.cons.length - 1 ? '1px solid rgba(255,107,53,.1)' : 'none',
                    fontSize: '14px', color: 'var(--text-secondary)',
                  }}>
                    <Tag size="small" theme="danger" variant="outline" style={{ marginRight: '8px', borderColor: '#FF6B35', color: '#FF6B35' }}>CON</Tag>{c}
                  </div>
                ))}
              </div>
            </div>

            {/* 风险标记 */}
            {deepseekData.risk_flags?.length > 0 && (
              <div className="glass-card" style={{ padding: '22px 28px', marginTop: '16px' }}>
                <h5 style={{ margin: '0 0 14px', color: '#FF6B35', fontSize: '14px', fontWeight: 700 }}>
                  🚨 RISK FLAGS ({deepseekData.risk_flags.length})
                </h5>
                {deepseekData.risk_flags.map((rf, i) => (
                  <Alert key={i} theme="error" message={rf} style={{ marginBottom: '8px' }} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ====== 六维雷达评分（6路并行 DeepSeek） ====== */}
      <div className="glass-card" style={{ padding: '28px 32px', marginBottom: '28px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '20px', flexWrap: 'wrap', gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '18px' }}>🎯</span>
            <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '16px', fontWeight: 600 }}>
              Six-Dimension Radar Score
            </h4>
            <Tag variant="light" size="small"
              style={{ background: 'rgba(0,212,255,.1)', color: '#00D4FF', border: 'none' }}
            >6× DeepSeek</Tag>
            {dimScores && (
              <Tag variant="light" size="small"
                style={{ background: 'rgba(74,255,145,.08)', color: '#4AFF91', border: 'none' }}
              >PERSISTED</Tag>
            )}
          </div>
          <Button
            theme="primary"
            variant="outline"
            size="large"
            loading={dimLoading}
            onClick={handleDimensionAnalyze}
            style={{ borderColor: 'rgba(0,212,255,.5)', color: '#00D4FF' }}
          >
            {dimLoading ? '6 Engine Scoring...' : 'Begin 6D Scoring'}
          </Button>
        </div>

        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '13px' }}>
          并行调用 6 路 DeepSeek，分别聚焦学术水平、指导风格、人品师德、师生关系、科研经费、学生出路六个维度进行专业推断。
        </p>

        {dimError && (
          <Alert theme="error" message={dimError} style={{ marginBottom: '16px' }} />
        )}

        {dimLoading && <Loading text="DeepSeek evaluating 6 dimensions..." />}

        {dimScores && !dimLoading && (
          <div style={{ animation: 'fadeInUp .4s ease-out both' }}>
            {/* 雷达图 */}
            <RadarChart data={dimScores} />

            {/* 综合分 + 置信度 */}
            <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
              <div className="glass-card" style={{
                flex: 1, textAlign: 'center', padding: '18px 16px',
                background: 'rgba(0,212,255,.04)', border: '1px solid rgba(0,212,255,.15)',
              }}>
                <div style={{ fontSize: '40px', fontWeight: 900, color: '#00D4FF', lineHeight: 1 }}>
                  {dimScores.overall.toFixed(1)}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '4px', letterSpacing: '1px' }}>
                  WEIGHTED OVERALL
                </div>
              </div>
              <div className="glass-card" style={{
                flex: 1, textAlign: 'center', padding: '18px 16px',
                background: confidenceColor(dimScores.confidence).bg,
                border: `1px solid ${confidenceColor(dimScores.confidence).border}`,
              }}>
                <div style={{
                  fontSize: '40px', fontWeight: 900,
                  color: confidenceColor(dimScores.confidence).color,
                  lineHeight: 1,
                }}>
                  {(dimScores.confidence * 100).toFixed(0)}%
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '4px', letterSpacing: '1px' }}>
                  CONFIDENCE
                </div>
              </div>
            </div>

            {/* 各维度详细评分 */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              {(['academic', 'mentorship', 'ethics', 'relationship', 'funding', 'career'] as const).map(dimKey => {
                const dim = dimScores[dimKey]
                const label = dimLabels[dimKey]
                return (
                  <DimCard
                    key={dimKey}
                    label={label.cn}
                    score={dim.score}
                    reasoning={dim.reasoning || ''}
                    redFlags={dim.red_flags || []}
                  />
                )
              })}
            </div>

            {/* 交叉维度 Red Flag 汇总 */}
            {redFlagsSummary.length > 0 && (
              <div className="glass-card" style={{
                padding: '18px 24px', marginTop: '16px',
                border: '1px solid rgba(255,107,53,.2)', background: 'rgba(255,107,53,.03)',
              }}>
                <h5 style={{ margin: '0 0 10px', color: '#FF6B35', fontSize: '13px', fontWeight: 700 }}>
                  🚨 CROSS-DIMENSION RED FLAGS ({redFlagsSummary.length})
                </h5>
                {redFlagsSummary.map((rf, i) => (
                  <Alert key={i} theme="error" message={rf} style={{ marginBottom: '6px' }} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ====== 已保存分析 ====== */}
      <div className="glass-card" style={{ padding: '28px 32px', marginBottom: '28px' }}>
        <SavedAnalysesSection />
      </div>

      {/* Advisor Detail — 跳转导师详情页 */}
      <div className="glass-card" style={{
        textAlign: 'center', padding: '24px 32px', marginBottom: '24px',
        borderColor: 'rgba(0,212,255,.15)',
      }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '14px' }}>
          View all reviews aggregated with DeepSeek AI advisor profile.
        </p>
        <Button
          theme="primary"
          variant="outline"
          size="large"
          onClick={() => navigate('/advisor', { state: { result } })}
          style={{ borderColor: 'rgba(0,212,255,.5)', color: '#00D4FF', width: '100%' }}
        >
          Advisor Detail
        </Button>
      </div>

      <div style={{ textAlign: 'center', paddingBottom: '40px' }}>
        <Space>
          <Link to="/search"><Button variant="outline">← Back to Results</Button></Link>
          <Link to="/"><Button variant="outline">Home</Button></Link>
        </Space>
      </div>
    </div>
  )
}

// ─── 已保存分析列表 ──────────────────────────────────────

function SavedAnalysesSection() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<api.AnalysisRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadList() }, [])

  async function loadList() {
    setLoading(true)
    try {
      const data = await api.fetchAnalysisList()
      setRecords(data.records)
    } catch { /* 静默 */ }
    finally { setLoading(false) }
  }

  async function handleDelete(id: number) {
    if (!confirm('确定删除这条分析记录？')) return
    try {
      await api.deleteAnalysisRecord(id)
      loadList()
      await MessagePlugin.success('已删除')
    } catch (e: any) {
      await MessagePlugin.error(e.message || '删除失败')
    }
  }

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span style={{ fontSize: '18px' }}>{'\uD83D\uDCBE'}</span>
        <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '16px', fontWeight: 600 }}>
          Saved Analyses
        </h4>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {records.length} records persisted in database
        </span>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>Loading...</p>
      ) : records.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
          No saved analyses yet. Run SnowNLP or DeepSeek analysis to persist results.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {records.map(rec => (
            <div key={rec.id} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', borderRadius: '10px',
              background: 'rgba(0,0,0,.2)', border: '1px solid var(--border-color)',
            }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#E8EDF5' }}>
                  {rec.advisor_name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                  {[rec.university, rec.department].filter(Boolean).join(' · ') || '(unknown)'}
                  {' · '}{rec.review_count} reviews
                  {' · '}{new Date(rec.updated_at).toLocaleDateString('zh-CN')}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={() => navigate('/history')} style={{
                  background: 'rgba(0,212,255,.08)', border: '1px solid rgba(0,212,255,.2)',
                  color: '#00D4FF', borderRadius: '6px', padding: '4px 12px',
                  fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
                }}>{'\uD83D\uDD0D'} View</button>
                <button onClick={() => handleDelete(rec.id)} style={{
                  background: 'rgba(255,82,82,.08)', border: '1px solid rgba(255,82,82,.2)',
                  color: '#ff5252', borderRadius: '6px', padding: '4px 10px',
                  fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
                }}>{'\u2715'}</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

/** 统计徽章 */
function StatBadge({ label, value, theme }: { label: string; value: number; theme: string }) {
  return (
    <Tag
      variant="light-outline"
      size="large"
      style={{
        borderColor: `${theme}33`, color: theme,
        padding: '4px 16px', fontSize: '13px', borderRadius: '8px',
      }}
    >
      <strong>{value}</strong> {label.toUpperCase()}
    </Tag>
  )
}

// ─── 维度中文标签 ──────────────────────────────────────

const dimLabels: Record<string, { cn: string; full: string }> = {
  academic:     { cn: '学术水平', full: 'Academic' },
  mentorship:   { cn: '指导风格', full: 'Mentorship' },
  ethics:       { cn: '人品师德', full: 'Ethics' },
  relationship: { cn: '师生关系', full: 'Relationship' },
  funding:      { cn: '科研经费', full: 'Funding' },
  career:       { cn: '学生出路', full: 'Career' },
}

/** 置信度颜色映射 */
function confidenceColor(confidence: number): { bg: string; border: string; color: string } {
  if (confidence >= 0.8) return {
    bg: 'rgba(74,255,145,.04)',
    border: 'rgba(74,255,145,.15)',
    color: '#4AFF91',
  }
  if (confidence >= 0.5) return {
    bg: 'rgba(255,200,50,.04)',
    border: 'rgba(255,200,50,.15)',
    color: '#FFD54F',
  }
  return {
    bg: 'rgba(255,107,53,.04)',
    border: 'rgba(255,107,53,.15)',
    color: '#FF6B35',
  }
}

/** 全部评论浏览组件 — 可折叠，默认展示前 4 条 */
function ReviewBrowser({ reviews }: { reviews: api.ReviewItem[] | undefined }) {
  const [expanded, setExpanded] = useState(false)
  if (!reviews?.length) return null

  const previewCount = 4
  const hasMore = reviews.length > previewCount
  const visible = expanded ? reviews : reviews.slice(0, previewCount)

  return (
    <div className="glass-card" style={{ padding: '28px 32px', marginBottom: '24px' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '18px' }}>{'\uD83D\uDCDD'}</span>
          <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '16px', fontWeight: 600 }}>
            All Reviews
          </h4>
          <Tag variant="light" size="small"
            style={{ background: 'rgba(100,130,180,.08)', color: 'var(--text-secondary)', border: 'none' }}
          >{reviews.length} total</Tag>
        </div>
        {hasMore && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              background: 'rgba(0,212,255,.06)', border: '1px solid rgba(0,212,255,.15)',
              borderRadius: '8px', color: '#00D4FF', fontSize: '12px', cursor: 'pointer',
              padding: '6px 16px', fontFamily: 'inherit',
              transition: 'all .2s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(0,212,255,.12)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(0,212,255,.06)'
            }}
          >
            {expanded ? 'Collapse ▲' : `Show All ${reviews.length} ▼`}
          </button>
        )}
      </div>

      <div style={{
        maxHeight: expanded ? 'none' : '360px',
        overflowY: 'auto',
        display: 'flex', flexDirection: 'column', gap: '12px',
      }}>
        {visible.map((review, i) => (
          <div key={i} style={{
            padding: '14px 18px',
            background: 'rgba(0,0,0,.2)',
            borderRadius: '10px',
            borderBottom: '1px solid rgba(100,130,180,.06)',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px',
            }}>
              <span>{review.author || 'anonymous'}{' · '}{review.date || ''}</span>
              {review.rating != null && (
                <span style={{
                  color: review.rating >= 7 ? '#4AFF91' : review.rating <= 4 ? '#FF6B35' : '#FFD54F',
                }}>
                  {'★'.repeat(Math.round((review.rating ?? 0) / 2))}
                  {'☆'.repeat(5 - Math.round((review.rating ?? 0) / 2))}
                  {' '}{review.rating}/10
                </span>
              )}
            </div>
            <p style={{
              margin: 0, fontSize: '13.5px', lineHeight: 1.7,
              color: 'var(--text-secondary)', whiteSpace: 'pre-wrap',
            }}>
              {review.content}
            </p>
            {review.source_url && (
              <a
                href={review.source_url.startsWith('http') ? review.source_url : `https://${review.source}`}
                target="_blank" rel="noreferrer"
                style={{
                  display: 'inline-block', marginTop: '8px',
                  fontSize: '11px', color: '#00D4FF', textDecoration: 'none',
                  opacity: .6,
                }}
              >
                view on {review.source || 'source'} →
              </a>
            )}
          </div>
        ))}
      </div>

      {/* 底部展开按钮 — 方便滚动到底后操作 */}
      {hasMore && expanded && (
        <button
          onClick={() => setExpanded(false)}
          style={{
            display: 'block', width: '100%', textAlign: 'center',
            background: 'rgba(0,212,255,.04)',
            border: '1px solid rgba(0,212,255,.1)', borderRadius: '8px',
            color: 'var(--text-muted)', fontSize: '12px', cursor: 'pointer',
            padding: '8px 0', marginTop: '12px', fontFamily: 'inherit',
            transition: 'all .2s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#00D4FF' }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
        >
          Collapse Reviews ▲
        </button>
      )}
    </div>
  )
}

/** 维度卡片 — 可展开推理文本 */
function DimCard({ label, score, reasoning, redFlags }: {
  label: string
  score: number
  reasoning: string
  redFlags: string[]
}) {
  const [expanded, setExpanded] = useState(false)
  const maxLen = 100  // 预览截断阈值
  const needExpand = reasoning.length > maxLen

  const scoreColor = score >= 7 ? '#4AFF91' : score >= 5 ? '#FFD54F' : '#FF6B35'
  const bgColor   = score >= 7 ? 'rgba(74,255,145,.03)' : score >= 5 ? 'rgba(255,200,50,.03)' : 'rgba(255,107,53,.03)'
  const borderColor = score >= 7 ? 'rgba(74,255,145,.12)' : score >= 5 ? 'rgba(255,200,50,.12)' : 'rgba(255,107,53,.12)'

  return (
    <div className="glass-card" style={{
      padding: '14px 16px', background: bgColor, border: `1px solid ${borderColor}`,
      transition: 'all .2s',
    }}>
      {/* 标题行：维度名 + 评分 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <span style={{ fontSize: '13px', fontWeight: 600, color: '#E8EDF5' }}>{label}</span>
        <span style={{ fontSize: '22px', fontWeight: 900, color: scoreColor }}>
          {score.toFixed(1)}
        </span>
      </div>

      {/* 推理文本 */}
      <p style={{
        margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.65,
        whiteSpace: needExpand && !expanded ? undefined : 'pre-wrap',
        overflow: needExpand && !expanded ? 'hidden' : 'visible',
        display: needExpand && !expanded ? '-webkit-box' : 'block',
        WebkitLineClamp: needExpand && !expanded ? 2 : 'unset',
        WebkitBoxOrient: needExpand && !expanded ? 'vertical' : 'unset',
      }}>
        {reasoning || '—'}
      </p>

      {/* 展开 / 收起按钮 */}
      {needExpand && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none', border: 'none', color: '#00D4FF',
            fontSize: '11px', cursor: 'pointer', padding: '4px 0 0',
            fontFamily: 'inherit', display: 'block', width: '100%', textAlign: 'left',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#4AFF91' }}
          onMouseLeave={e => { e.currentTarget.style.color = '#00D4FF' }}
        >
          {expanded ? '收起 ▲' : `展开全文 ▼`}
        </button>
      )}

      {/* 红色警报 */}
      {redFlags.length > 0 && (
        <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,107,53,.15)' }}>
          {redFlags.map((rf, i) => (
            <span key={i} style={{
              display: 'inline-block', margin: '2px 4px 2px 0', padding: '2px 8px',
              borderRadius: '4px', fontSize: '11px',
              background: 'rgba(255,107,53,.1)', color: '#FF6B35',
              border: '1px solid rgba(255,107,53,.2)',
            }}>🚨 {rf}</span>
          ))}
        </div>
      )}
    </div>
  )
}
