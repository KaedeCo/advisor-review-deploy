import { useNavigate } from 'react-router-dom'
import CoolSlogan from '../components/CoolSlogan'
import SearchForm from '../components/SearchForm'

/**
 * 主页 — 全屏星空英雄区 + Slogan + 搜索
 */
export default function HomePage() {
  const navigate = useNavigate()

  const handleSearch = (data: { name: string; university: string; department: string }) => {
    navigate('/search', { state: data })
  }

  return (
    <div style={{
      minHeight: 'calc(100vh - 64px)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 20px',
      position: 'relative',
    }}>
      {/* 装饰性光晕 */}
      <div style={{
        position: 'absolute', top: '15%', left: '50%',
        transform: 'translateX(-50%)', width: '500px', height: '300px',
        background: 'radial-gradient(ellipse, rgba(0,212,255,.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* 主内容 */}
      <div className="animate-in" style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <CoolSlogan />
        <SearchForm onSubmit={handleSearch} />
      </div>

      {/* 底部提示 */}
      <p style={{
        marginTop: '40px',
        fontSize: '12px',
        color: 'var(--text-muted)',
        letterSpacing: '2px',
      }}>
        // MULTI-PLATFORM ADVISOR REVIEW AGGREGATOR v1.0
      </p>
    </div>
  )
}
