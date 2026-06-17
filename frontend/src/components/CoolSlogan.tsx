/**
 * COOL 轨道动画 Slogan — 暗色主题版
 */
export default function CoolSlogan() {
  return (
    <div style={{ marginBottom: '48px' }}>
      <p className="slogan-text" style={{
        fontSize: '32px', fontWeight: 300, color: '#E8EDF5',
        letterSpacing: '3px',
      }}>
        We just define some C
        <span className="orbit-container">
          <span className="orbit-o o1">O</span>
          <span className="orbit-center" />
          <span className="orbit-o o2">O</span>
        </span>
        L things.
      </p>

      {/* 副标语 */}
      <p style={{
        marginTop: '20px', fontSize: '15px',
        background: 'linear-gradient(90deg, #4A9EFF, #00D4FF, #4AFF91)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        letterSpacing: '6px',
        textTransform: 'uppercase',
      }}>
        Multi-Source Aggregation &middot; AI-Powered Analysis &middot; Objective Insight
      </p>
    </div>
  )
}
