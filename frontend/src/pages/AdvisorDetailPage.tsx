import { useState, useEffect, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Button, Tag, Loading, Alert, MessagePlugin } from 'tdesign-react'
import * as api from '../services/api'

/**
 * 导师详情页 — 集中展示所有评论 + DeepSeek 聚合画像
 */
export default function AdvisorDetailPage() {
  const location = useLocation()
  const [result, setResult] = useState<api.AdvisorResult | null>(null)
  const [profile, setProfile] = useState<api.AdvisorProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [showAllReviews, setShowAllReviews] = useState(false)

  useEffect(() => {
    if (location.state?.result) {
      setResult(location.state.result as api.AdvisorResult)
    }
  }, [])

  // 尝试从数据库恢复已保存的画像
  useEffect(() => {
    if (!result?.name) return
    loadSavedProfile(result.name)
  }, [result?.name])

  async function loadSavedProfile(advisorName: string) {
    try {
      const list = await api.fetchAnalysisList()
      const match = list.records.find(r => r.advisor_name === advisorName)
      if (match) {
        const detail = await api.fetchAnalysisDetail(match.id)
        if ((detail as any).advisor_profile) {
          setProfile((detail as any).advisor_profile)
        }
      }
    } catch { /* 静默 */ }
  }

  const reviewsText = useMemo(
    () => result?.reviews?.map(r => `[${r.author || 'anonymous'}] ${r.content}`).join('\n\n') || '',
    [result]
  )

  async function handleGenerateProfile() {
    if (!reviewsText) return
    setProfileLoading(true)
    setProfileError('')
    try {
      const data = await api.generateProfile(reviewsText, {
        name: result?.name,
        university: result?.university,
        department: result?.department,
      })
      setProfile(data)
      await MessagePlugin.success('导师画像生成完成')
    } catch (e: any) {
      setProfileError(e.message || 'DeepSeek 生成失败')
      await MessagePlugin.error(e.message || 'DeepSeek 生成失败')
    } finally {
      setProfileLoading(false)
    }
  }

  if (!result) {
    return (
      <div className="page-container" style={{ textAlign: 'center', paddingTop: '80px' }}>
        <Alert theme="warning" message="No data received. Please search for an advisor first." />
        <br />
        <Link to="/"><Button variant="outline">Back to Search</Button></Link>
      </div>
    )
  }

  const reviews = result.reviews || []
  const previewCount = 5
  const visibleReviews = showAllReviews ? reviews : reviews.slice(0, previewCount)

  // 风险等级颜色
  const riskColor = profile?.risk_level === '低风险' ? '#4AFF91'
    : profile?.risk_level === '高风险' ? '#FF6B35' : '#FFD54F'

  return (
    <div className="page-container">
      {/* 导师信息头 */}
      <div className="glass-card scanline" style={{
        padding: '24px 32px',
        marginBottom: '24px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '22px' }}>
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
            {reviews.length} reviews
          </div>
        </div>
        <Link to="/search">
          <Button variant="outline" size="small">Back to Results</Button>
        </Link>
      </div>

      {/* 导师画像区域 */}
      <div className="glass-card" style={{ padding: '28px 32px', marginBottom: '24px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: '20px', flexWrap: 'wrap', gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '18px' }}>{'\uD83D\uDD0D'}</span>
            <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '16px', fontWeight: 600 }}>
              Advisor Profile (DeepSeek)
            </h4>
          </div>
          <Button
            theme="primary"
            variant="outline"
            size="small"
            loading={profileLoading}
            onClick={handleGenerateProfile}
            disabled={!reviews.length}
            style={{ borderColor: 'rgba(0,212,255,.5)', color: '#00D4FF' }}
          >
            {profileLoading ? 'AI Generating...' : profile ? 'Regenerate Profile' : 'Generate Profile'}
          </Button>
        </div>

        {profileError && (
          <Alert theme="error" message={profileError} style={{ marginBottom: '16px' }} />
        )}

        {profileLoading && <Loading text="DeepSeek analyzing advisor profile..." />}

        {profile && !profileLoading && (
          <div style={{ animation: 'fadeInUp .4s ease-out both' }}>
            {/* 一句话总结 */}
            {profile.one_line_summary && (
              <div style={{
                textAlign: 'center', padding: '20px', marginBottom: '20px',
                borderRadius: '14px',
                background: 'linear-gradient(135deg, rgba(0,212,255,.04), rgba(0,212,255,.01))',
                border: '1px solid rgba(0,212,255,.12)',
              }}>
                <p style={{
                  margin: 0, fontSize: '16px', lineHeight: 1.7,
                  color: '#E8EDF5', fontStyle: 'italic',
                }}>
                  "{profile.one_line_summary}"
                </p>
              </div>
            )}

            {/* 风险等级 + 关键词 */}
            <div style={{
              display: 'flex', gap: '12px', marginBottom: '20px',
              flexWrap: 'wrap', alignItems: 'center',
            }}>
              {profile.risk_level && (
                <Tag
                  variant="light"
                  size="large"
                  style={{
                    background: `${riskColor}15`, color: riskColor,
                    border: `1px solid ${riskColor}30`,
                    borderRadius: '8px', fontWeight: 700,
                  }}
                >
                  {profile.risk_level}
                </Tag>
              )}
              {profile.keywords?.map((kw, i) => (
                <Tag key={i} variant="outline" size="small"
                  style={{
                    borderColor: 'rgba(100,130,180,.2)',
                    color: 'var(--text-secondary)',
                    borderRadius: '6px',
                  }}
                >
                  {kw}
                </Tag>
              ))}
            </div>

            {/* 多维画像网格 */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '14px',
            }}>
              {profile.teaching_style && (
                <ProfileCard icon="🎯" title="指导风格" content={profile.teaching_style} color="#00D4FF" />
              )}
              {profile.personality && (
                <ProfileCard icon="🧑" title="人品师德" content={profile.personality} color="#4AFF91" />
              )}
              {profile.research_strength && (
                <ProfileCard icon="📚" title="学术水平" content={profile.research_strength} color="#FFD54F" />
              )}
              {profile.student_outcome && (
                <ProfileCard icon="🎓" title="学生出路" content={profile.student_outcome} color="#B088F9" />
              )}
            </div>

            {/* 总体推荐 */}
            {profile.overall_recommendation && (
              <div style={{
                marginTop: '16px', padding: '16px 20px',
                borderRadius: '12px',
                background: 'rgba(176,136,249,.04)',
                border: '1px solid rgba(176,136,249,.12)',
              }}>
                <h5 style={{
                  margin: '0 0 8px', color: '#B088F9', fontSize: '13px',
                  fontWeight: 700,
                }}>Overall Recommendation</h5>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.7 }}>
                  {profile.overall_recommendation}
                </p>
              </div>
            )}
          </div>
        )}

        {!profile && !profileLoading && !profileError && reviews.length > 0 && (
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '16px' }}>
            Click "Generate Profile" to let DeepSeek AI aggregate all reviews into a comprehensive advisor profile.
          </p>
        )}
      </div>

      {/* 全部评论集中展示 */}
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
          {reviews.length > previewCount && (
            <button
              onClick={() => setShowAllReviews(!showAllReviews)}
              style={{
                background: 'rgba(0,212,255,.06)', border: '1px solid rgba(0,212,255,.15)',
                borderRadius: '8px', color: '#00D4FF', fontSize: '12px', cursor: 'pointer',
                padding: '6px 16px', fontFamily: 'inherit',
              }}
            >
              {showAllReviews ? 'Collapse ▲' : `Show All ${reviews.length} ▼`}
            </button>
          )}
        </div>

        <div style={{
          maxHeight: showAllReviews ? 'none' : '400px',
          overflowY: 'auto',
          display: 'flex', flexDirection: 'column', gap: '12px',
        }}>
          {visibleReviews.map((review, i) => (
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
            </div>
          ))}
        </div>
      </div>

      <div style={{ textAlign: 'center', paddingBottom: '40px' }}>
        <Link to="/search"><Button variant="outline">Back to Results</Button></Link>
        <span style={{ margin: '0 8px' }} />
        <Link to="/analysis"><Button variant="outline">Full Analysis</Button></Link>
      </div>
    </div>
  )
}

function ProfileCard({ icon, title, content, color }: {
  icon: string
  title: string
  content: string
  color: string
}) {
  return (
    <div className="glass-card" style={{
      padding: '16px 18px',
      background: `${color}04`,
      border: `1px solid ${color}15`,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px',
      }}>
        <span style={{ fontSize: '14px' }}>{icon}</span>
        <span style={{ fontSize: '13px', fontWeight: 600, color }}>{title}</span>
      </div>
      <p style={{
        margin: 0, fontSize: '13px', lineHeight: 1.7,
        color: 'var(--text-secondary)',
      }}>
        {content}
      </p>
    </div>
  )
}
