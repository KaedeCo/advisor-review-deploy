import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Tag, Button, Empty } from 'tdesign-react'
import type { AdvisorResult } from '../services/api'

interface Props {
  results: AdvisorResult[]
  onAnalyze?: (result: AdvisorResult) => void
}

/**
 * 搜索结果卡片 — 暗色玻璃拟态
 */
export default function ResultCards({ results, onAnalyze }: Props) {
  if (!results.length) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '48px' }}>
        <Empty description="未找到相关评价数据" />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {results.map((r, idx) => (
        <ResultCardItem key={idx} result={r} onAnalyze={onAnalyze} />
      ))}
    </div>
  )
}

/** 单个结果卡片 — 内含可展开评论 */
function ResultCardItem({ result: r, onAnalyze }: { result: AdvisorResult; onAnalyze?: Props['onAnalyze'] }) {
  const navigate = useNavigate()
  const [showAllReviews, setShowAllReviews] = useState(false)
  const previewCount = 3
  const hasMore = (r.reviews?.length ?? 0) > previewCount
  const visibleReviews = showAllReviews ? (r.reviews ?? []) : (r.reviews ?? []).slice(0, previewCount)

  return (
    <Card
      bordered={false}
      hover
      className="glass-card scanline"
      style={{
        transition: 'all .25s',
        overflow: 'hidden',
        background: 'var(--bg-glass)',
        border: '1px solid var(--border-color)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'rgba(0,212,255,.25)'
        e.currentTarget.style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--border-color)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        {/* 左侧：导师信息 */}
        <div>
          <h3 style={{ margin: '0 0 8px', fontSize: '18px', color: '#E8EDF5' }}>
            {r.name}
            {r.overall_score !== null && r.overall_score !== undefined && (
              <Tag
                theme="primary" variant="light"
                size="small"
                style={{
                  marginLeft: '10px', borderRadius: '6px',
                  background: r.overall_score! >= 7 ? 'rgba(74,255,145,.12)' : r.overall_score! >= 5 ? 'rgba(255,200,50,.12)' : 'rgba(255,107,53,.12)',
                  borderColor: r.overall_score! >= 7 ? 'rgba(74,255,145,.3)' : r.overall_score! >= 5 ? 'rgba(255,200,50,.3)' : 'rgba(255,107,53,.3)',
                  color: r.overall_score! >= 7 ? '#4AFF91' : r.overall_score! >= 5 ? '#FFD54F' : '#FF6B35',
                }}
              >
                ★ {r.overall_score}/10
              </Tag>
            )}
          </h3>

          <div style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '10px' }}>
            {[r.university, r.department].filter(Boolean).join(' · ') || ''}
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <Tag variant="outline" size="small"
              style={{ borderColor: 'rgba(0,212,255,.3)', color: '#00D4FF' }}
            >
              {r.source}
            </Tag>
            <span style={{ color: 'rgba(100,130,180,.3)' }}>·</span>
            <Tag variant="light" size="small"
              style={{ background: 'rgba(100,130,180,.08)', border: 'none', color: 'var(--text-secondary)' }}
            >
              {r.review_count} reviews
            </Tag>
          </div>
        </div>

        {/* 右侧：操作 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
          {r.detail_url && (
            <a href={r.detail_url.startsWith('http') ? r.detail_url : `https://gradchoice.org${r.detail_url}`}
              target="_blank" rel="noreferrer"
              style={{
                fontSize: '13px', color: '#00D4FF', textDecoration: 'none',
                padding: '4px 0',
                transition: '.2s',
              }}
            >
              Source Link
            </a>
          )}
          <div style={{ display: 'flex', gap: '6px' }}>
            <Button
              size="small" variant="outline"
              onClick={() => navigate('/advisor', { state: { result: r } })}
              style={{
                borderColor: 'rgba(0,212,255,.4)', color: '#00D4FF',
                borderRadius: '8px',
              }}
            >
              Detail
            </Button>
            {onAnalyze && (
              <Button
                size="small" variant="outline"
                onClick={() => onAnalyze(r)}
                style={{
                  borderColor: 'rgba(176,136,249,.4)', color: '#B088F9',
                  borderRadius: '8px',
                }}
              >
                Analyze
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* 评论列表 — 可展开/收起 */}
      {(r.reviews?.length ?? 0) > 0 && (
        <div style={{
          marginTop: '18px',
          padding: '14px 18px',
          background: 'rgba(0,0,0,.25)',
          borderRadius: '10px',
          maxHeight: showAllReviews ? 'none' : '280px',
          overflowY: showAllReviews ? 'visible' : 'auto',
          borderLeft: '2px solid rgba(0,212,255,.15)',
        }}>
          {visibleReviews.map((review, ri) => (
            <div key={ri} style={{
              marginBottom: ri < visibleReviews.length - 1 ? '12px' : '0',
              paddingBottom: ri < visibleReviews.length - 1 ? '12px' : '0',
              borderBottom: ri < visibleReviews.length - 1 ? '1px solid rgba(100,130,180,.08)' : 'none',
            }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                {review.author || 'anonymous'} · {review.date || ''}
                {review.rating != null && (
                  <span style={{
                    marginLeft: '10px',
                    color: review.rating >= 7 ? '#4AFF91' : review.rating <= 4 ? '#FF6B35' : '#FFD54F',
                  }}>
                    {'★'.repeat(Math.round((review.rating ?? 0) / 2))}
                    {'☆'.repeat(5 - Math.round((review.rating ?? 0) / 2))}
                    {' '}{review.rating}/10
                  </span>
                )}
              </div>
              <p style={{ fontSize: '13.5px', lineHeight: 1.65, margin: 0, color: 'var(--text-secondary)' }}>
                {review.content}
              </p>
            </div>
          ))}

          {/* 展开/收起按钮 */}
          {hasMore && (
            <button
              onClick={() => setShowAllReviews(!showAllReviews)}
              style={{
                display: 'block', width: '100%', textAlign: 'center',
                background: 'rgba(0,212,255,.06)',
                border: '1px solid rgba(0,212,255,.15)',
                borderRadius: '8px', color: '#00D4FF',
                fontSize: '13px', cursor: 'pointer', padding: '8px 0', marginTop: '8px',
                fontFamily: 'inherit',
                transition: 'all .2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(0,212,255,.12)'
                e.currentTarget.style.borderColor = 'rgba(0,212,255,.35)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(0,212,255,.06)'
                e.currentTarget.style.borderColor = 'rgba(0,212,255,.15)'
              }}
            >
              {showAllReviews
                ? `收起全部 ▲ (共 ${r.reviews!.length} 条)`
                : `查看全部 ${r.reviews!.length} 条评论 ▼`}
            </button>
          )}
        </div>
      )}
    </Card>
  )
}
