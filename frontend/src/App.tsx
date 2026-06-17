import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import AnalysisPage from './pages/AnalysisPage'
import SettingsPage from './pages/SettingsPage'
import HistoryPage from './pages/HistoryPage'
import AdvisorDetailPage from './pages/AdvisorDetailPage'
import DisclaimerPage from './pages/DisclaimerPage'
import KpiSidebar from './components/KpiSidebar'

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div style={{ minHeight: '100vh', background: 'transparent' }}>
        {/* 顶部导航 — 玻璃拟态 */}
        <header style={{
          position: 'sticky', top: 0, zIndex: 100,
          background: 'rgba(10,14,23,0.8)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(0,212,255,0.1)',
          padding: '0 40px',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            height: '64px', maxWidth: '1200px', margin: '0 auto',
          }}>
            {/* Logo */}
            <Link to="/" style={{ textDecoration: 'none' }}>
              <span style={{
                fontSize: '20px', fontWeight: 800,
                background: 'linear-gradient(135deg, #00D4FF, #4AFF91)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '1px',
              }}>
                ADVISOR.SCAN
              </span>
            </Link>

            {/* 导航链接 */}
            <nav style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {[
                { to: '/', label: '首页' },
                { to: '/search', label: '搜索' },
                { to: '/history', label: '历史' },
                { to: '/analysis', label: '分析' },
                { to: '/settings', label: '设置' },
                { to: '/disclaimer', label: '免责声明' },
              ].map(item => (
                <Link key={item.to} to={item.to}
                  style={{
                    textDecoration: 'none', color: 'var(--text-secondary)',
                    fontSize: '14px', padding: '6px 16px', borderRadius: '8px',
                    transition: 'all .2s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.color = '#00D4FF'
                    e.currentTarget.style.background = 'rgba(0,212,255,0.08)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.color = 'var(--text-secondary)'
                    e.currentTarget.style.background = 'transparent'
                  }}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        {/* KPI 监控侧边栏 */}
        <KpiSidebar />

        {/* 页面内容 */}
        <main style={{ padding: '32px 0 60px' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/advisor" element={<AdvisorDetailPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/disclaimer" element={<DisclaimerPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
