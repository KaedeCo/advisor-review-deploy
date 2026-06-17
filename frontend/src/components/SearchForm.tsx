import { useState, useRef, forwardRef } from 'react'

interface SearchFormData {
  name: string
  university: string
  department: string
}

interface Props {
  onSubmit: (data: SearchFormData) => void
}

// ─── PillInput（非受控组件，通过 ref 读取值）───────────────
interface PillInputProps {
  label: string
  placeholder: string
  icon: React.ReactNode
  accent: string
  required?: boolean
  onEnter?: () => void
}

const PillInput = forwardRef<HTMLInputElement, PillInputProps>(
  function PillInput({ label, placeholder, icon, accent, required, onEnter }, ref) {
    return (
      <div style={{ width: '100%' }}>
        <label style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          fontSize: '12px', fontWeight: 600, letterSpacing: '2px',
          textTransform: 'uppercase' as const, color: `${accent}CC`,
          marginBottom: '10px',
        }}>
          {icon} {label}
          {required && <span style={{ color: '#FF6B35', fontSize: '14px' }}>*</span>}
        </label>

        <div style={{
          position: 'relative', display: 'flex', alignItems: 'center',
          borderRadius: '999px',
          background: `linear-gradient(${accent}15, ${accent}06)`,
          border: `1px solid ${accent}20`,
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          boxShadow: `
            inset 0 1px 1px rgba(255,255,255,.06),
            0 4px 24px rgba(0,0,0,.28),
            0 0 32px ${accent}06
          `,
          transition: 'all .35s ease',
          overflow: 'hidden',
        }}>
          <div style={{
            paddingLeft: '18px', paddingRight: '8px',
            opacity: .55, pointerEvents: 'none', flexShrink: 0,
          }}>
            {icon}
          </div>

          {/* 非受控 input — React 不干预输入过程，IME 完美兼容 */}
          <input
            ref={ref}
            type="text"
            defaultValue=""
            onKeyDown={onEnter ? (e) => { if (e.key === 'Enter') onEnter() } : undefined}
            placeholder={placeholder}
            style={{
              flex: 1, border: 'none', outline: 'none',
              background: 'transparent',
              color: '#E8EDF5',
              fontSize: '16px', fontWeight: 400,
              height: '52px', lineHeight: '52px',
              padding: '0 40px 0 2px',
              fontFamily: 'inherit',
              caretColor: accent,
            }}
          />

          {/* 清除按钮 —— 直接操作 DOM，不触发 React 渲染 */}
          <button
            type="button"
            style={{
              marginRight: '14px', flexShrink: 0,
              background: 'none', border: 'none',
              color: 'var(--text-muted)', cursor: 'pointer',
              fontSize: '16px', padding: '4px', lineHeight: 1,
              transition: '.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = accent }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
            onClick={() => {
              const el = (ref as React.RefObject<HTMLInputElement>).current
              if (el) {
                // 用原生 API 清空并聚焦，完全绕过 React
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                  window.HTMLInputElement.prototype, 'value'
                )?.set
                if (nativeInputValueSetter) {
                  nativeInputValueSetter.call(el, '')
                }
                el.dispatchEvent(new Event('input', { bubbles: true }))
                el.focus()
              }
            }}
          >
            ✕
          </button>

          <div style={{
            position: 'absolute', left: 0, top: '12%', bottom: '12%',
            width: '3px', borderRadius: '99px',
            background: `linear-gradient(180deg, ${accent}, ${accent}55)`,
            opacity: .6, pointerEvents: 'none',
          }} />
        </div>
      </div>
    )
  }
)

// ─── SearchForm 主组件 ─────────────────────────────────────
export default function SearchForm({ onSubmit }: Props) {
  const nameRef = useRef<HTMLInputElement>(null)
  const universityRef = useRef<HTMLInputElement>(null)
  const departmentRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)

  /** 提交：直接从 DOM ref 读取值，零中间状态 */
  const handleSubmit = () => {
    const name = nameRef.current?.value.trim()
    if (!name) return

    setLoading(true)
    try {
      onSubmit({
        name,
        university: universityRef.current?.value.trim() || '',
        department: departmentRef.current?.value.trim() || '',
      })
    } finally {
      setTimeout(() => setLoading(false), 300)
    }
  }

  return (
    <div className="glass-card scanline" style={{
      maxWidth: '720px', margin: '0 auto', padding: '44px 48px',
      position: 'relative', overflow: 'visible',
    }}>
      <div style={{
        position: 'absolute', top: 0, left: 60, right: 60, height: '1px',
        background: 'linear-gradient(90deg, transparent, rgba(0,212,255,.35), transparent)',
      }} />

      <form onSubmit={(e) => { e.preventDefault(); handleSubmit() }}>

        <PillInput
          ref={nameRef}
          label="Advisor Name"
          placeholder="Enter advisor's full name..."
          icon={<span style={{ fontSize: '18px' }}>👤</span>}
          accent="#00D4FF" required
          onEnter={handleSubmit}
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginTop: '26px' }}>
          <PillInput
            ref={universityRef}
            label="University"
            placeholder="e.g. Tsinghua University"
            icon={<span style={{ fontSize: '17px' }}>🏛️</span>}
            accent="#4AFF91"
          />
          <PillInput
            ref={departmentRef}
            label="Department"
            placeholder="e.g. Computer Science"
            icon={<span style={{ fontSize: '17px' }}>🔬</span>}
            accent="#B088F9"
          />
        </div>

        <div style={{ textAlign: 'center', marginTop: '38px' }}>
          <button
            type="submit" disabled={loading}
            onClick={handleSubmit}
            style={{
              minWidth: '320px', height: '56px',
              fontSize: '16px', fontWeight: 800,
              letterSpacing: '4px', textTransform: 'uppercase' as const,
              borderRadius: '999px',
              backgroundImage: loading ? undefined : 'linear-gradient(135deg, #00D4FF 0%, #0099CC 50%, #00D4FF 100%)',
              backgroundSize: '200% 200%',
              border: 'none',
              boxShadow: '0 4px 36px rgba(0,212,255,.32), inset 0 1px 0 rgba(255,255,255,.18), inset 0 -1px 0 rgba(0,0,0,.15)',
              animation: 'shimmer 3s ease-in-out infinite',
              position: 'relative', overflow: 'hidden', color: '#FFF',
              cursor: loading ? 'wait' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'SCANNING...' : (
              <>
                ▸ INITIATE SCAN
                <span style={{
                  position: 'absolute', top: '-50%', left: '-60%',
                  width: '40%', height: '200%',
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,.13), transparent)',
                  transform: 'skewX(-20deg)',
                  animation: 'btnShine 3s ease-in-out infinite',
                }} />
              </>
            )}
          </button>
        </div>
      </form>

      <p style={{
        textAlign: 'center', marginTop: '18px',
        fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '3px',
      }}>
        PRESS ENTER OR CLICK TO SEARCH
      </p>

      <style>{`
        input::placeholder {
          color: var(--text-muted);
          opacity: 0.5 !important;
        }
        @keyframes shimmer { 0%,100%{background-position:0% 50%} 50%{background-position:100% 50%} }
        @keyframes btnShine { 0%,80%,100%{left:-60%} 50%{left:160%} }
      `}</style>
    </div>
  )
}
