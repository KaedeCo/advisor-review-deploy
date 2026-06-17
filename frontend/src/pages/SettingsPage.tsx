import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from 'react-router-dom'
import * as api from '../services/api'

// ─── Toast ─────────────────────────────────────────────────
let toastTimer: ReturnType<typeof setTimeout> | null = null
function showToast(msg: string, type: 'success' | 'warning' | 'error' = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  const existing = document.getElementById('native-toast')
  if (existing) existing.remove()
  const colors = {
    success: { bg: 'rgba(74,255,145,.12)', border: 'rgba(74,255,145,.3)', text: '#4AFF91', icon: '\u2713' },
    warning: { bg: 'rgba(255,176,32,.12)', border: 'rgba(255,176,32,.3)', text: '#FFB020', icon: '!' },
    error: { bg: 'rgba(255,82,82,.12)', border: 'rgba(255,82,82,.3)', text: '#ff5252', icon: '\u2717' },
  }
  const c = colors[type]
  const el = document.createElement('div')
  el.id = 'native-toast'
  el.style.cssText = `
    position: fixed; top: 24px; right: 24px; z-index: 99999;
    background: ${c.bg}; border: 1px solid ${c.border}; color: ${c.text};
    padding: 10px 22px; border-radius: 10px; font-size: 13px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    display: flex; align-items: center; gap: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,.4);
    backdrop-filter: blur(16px); animation: toastIn .25s ease-out;
  `
  el.innerHTML = `<span style="font-weight:700">${c.icon}</span><span>${msg}</span>`
  document.body.appendChild(el)
  toastTimer = setTimeout(() => {
    el.style.opacity = '0'; el.style.transform = 'translateX(20px)'
    el.style.transition = '.25s'; setTimeout(() => el.remove(), 250)
  }, 2800)
}

// ─── Collapsible Section ───────────────────────────────────
function Section({
  icon, title, badge, defaultOpen = false, children,
}: {
  icon: string; title: string; badge?: string;
  defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="glass-card" style={{ marginBottom: '16px', overflow: 'hidden' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '12px',
          padding: '18px 24px', border: 'none', cursor: 'pointer',
          background: open ? 'rgba(255,255,255,.03)' : 'transparent',
          fontFamily: 'inherit', transition: '.2s',
          borderBottom: open ? '1px solid rgba(255,255,255,.06)' : 'none',
        }}
      >
        <span style={{ fontSize: '18px', flexShrink: 0 }}>{icon}</span>
        <h4 style={{ margin: 0, color: '#E8EDF5', fontSize: '15px', fontWeight: 600, flex: 1, textAlign: 'left' }}>
          {title}
        </h4>
        {badge && (
          <span style={{
            fontSize: '10px', color: '#4AFF91', border: '1px solid rgba(74,255,145,.3)',
            padding: '2px 8px', borderRadius: '4px', letterSpacing: '1px', textTransform: 'uppercase',
          }}>{badge}</span>
        )}
        <span style={{
          color: 'var(--text-muted)', fontSize: '12px', transition: '.2s',
          transform: open ? 'rotate(180deg)' : 'rotate(0)',
        }}>&#x25BC;</span>
      </button>
      {open && (
        <div style={{ padding: '20px 24px 28px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ─── Shared Button Style ───────────────────────────────────
function Btn({
  color, icon, children, disabled, onClick, style,
}: {
  color: string; icon?: string; children: React.ReactNode;
  disabled?: boolean; onClick?: () => void; style?: React.CSSProperties;
}) {
  return (
    <button
      onClick={onClick} disabled={disabled}
      style={{
        minWidth: icon ? '160px' : '140px', borderRadius: '10px',
        padding: '9px 22px', fontSize: '13px', fontWeight: 600,
        cursor: disabled ? 'wait' : 'pointer', fontFamily: 'inherit',
        background: `linear-gradient(135deg, ${color}18, ${color}08)`,
        border: `1px solid ${color}40`, color,
        transition: '.2s', opacity: disabled ? 0.6 : 1,
        boxShadow: disabled ? undefined : `0 0 16px ${color}08`,
        ...style,
      }}
    >{disabled ? 'WAIT...' : <>{icon} {children}</>}</button>
  )
}

// ─── Cookie Fields ─────────────────────────────────────────
interface CookieField { key: string; label: string; hint: string; required: boolean; color: string }

const COOKIE_FIELDS: CookieField[] = [
  { key: 'access_token', label: 'Access Token (JWT)', hint: 'GradChoice JWT token (starts with eyJ...)', required: true, color: '#FFB020' },
]

// ─── Main Page ─────────────────────────────────────────────
export default function SettingsPage() {
  const navigate = useNavigate()

  const [settings, setSettings] = useState<api.SettingsData | null>(null)
  const [dsKey, setDsKey] = useState('')
  const [cookieFields, setCookieFields] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    COOKIE_FIELDS.forEach(f => { init[f.key] = '' })
    return init
  })
  const [rawMode, setRawMode] = useState(false)
  const [rawCookie, setRawCookie] = useState('')
  const [customKeys, setCustomKeys] = useState<string[]>([])
  const [customValues, setCustomValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<api.TokenVerifyResult | null>(null)
  const [tavilyKey, setTavilyKey] = useState('')
  const [checkingTavily, setCheckingTavily] = useState(false)
  const [tavilyResult, setTavilyResult] = useState<api.TavilyCheckResult | null>(null)
  const [letpubCookie, setLetpubCookie] = useState('')
  const [verifyingLetpub, setVerifyingLetpub] = useState(false)
  const [letpubVerifyResult, setLetpubVerifyResult] = useState<{ valid: boolean; detail: string } | null>(null)

  useEffect(() => { loadSettings() }, [])

  async function loadSettings() {
    try {
      const data = await api.fetchSettings()
      setSettings(data)
      if (data.gradchoice_token_preview) {
        setCookieFields(prev => ({ ...prev, access_token: data.gradchoice_token_preview }))
        setRawCookie(data.gradchoice_token_preview)
      }
      if (data.letpub_cookie_preview) {
        setLetpubCookie(data.letpub_cookie_preview)
      }
      if (data.tavily_key_preview) {
        setTavilyKey(data.tavily_key_preview)
      }
    } catch (e) { console.error(e) }
  }

  function buildCookieString(): string {
    if (rawMode) return rawCookie.trim()
    const jwtVal = cookieFields['access_token']?.trim()
    if (jwtVal) return jwtVal
    const parts: string[] = []
    for (const k of customKeys) {
      const v = customValues[k]?.trim()
      if (k.trim() && v) parts.push(`${k.trim()}=${v}`)
    }
    return parts.join('; ')
  }

  function extractRawJWT(value: string): string {
    if (!value) return ''
    value = value.trim()
    if (value.startsWith('eyJ')) return value
    const m = value.match(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/)
    return m ? m[0] : value
  }

  function parseAndFill(raw: string) {
    const reset: Record<string, string> = {}
    COOKIE_FIELDS.forEach(f => { reset[f.key] = '' })
    setCookieFields(reset); setCustomValues({}); setCustomKeys([])
    if (!raw?.trim()) return
    const items = raw.split(';')
    for (const item of items) {
      const trimmed = item.trim()
      if (!trimmed || !trimmed.includes('=')) continue
      const eqIdx = trimmed.indexOf('=')
      const k = trimmed.substring(0, eqIdx).trim()
      const v = trimmed.substring(eqIdx + 1).trim()
      if (COOKIE_FIELDS.find(f => f.key === k)) {
        setCookieFields(prev => ({ ...prev, [k]: v }))
      } else {
        setCustomKeys(prev => prev.includes(k) ? prev : [...prev, k])
        setCustomValues(prev => ({ ...prev, [k]: v }))
      }
    }
  }

  async function handleSaveDeepseek() {
    if (!dsKey.trim()) { showToast('Enter API Key', 'warning'); return }
    if (dsKey.trim().length < 10) { showToast('Invalid API Key', 'warning'); return }
    setSaving(true)
    try {
      await api.updateDeepseekKey(dsKey.trim())
      showToast('DeepSeek API Key saved'); loadSettings()
    } catch (e: any) { showToast(e.message || 'Save failed', 'error') }
    finally { setSaving(false) }
  }

  async function handleVerifyToken() {
    setVerifying(true); setVerifyResult(null)
    try {
      const result = await api.verifyToken()
      setVerifyResult(result)
      showToast(result.valid ? 'Token valid' : 'Verification failed', result.valid ? 'success' : 'error')
    } catch (e: any) {
      setVerifyResult({ valid: false, status_code: 0, detail: e.message || 'Request failed', url: '' })
      showToast('Verify request failed', 'error')
    } finally { setVerifying(false) }
  }

  async function handleSaveCookie() {
    const toSave = extractRawJWT(buildCookieString())
    if (!toSave && !rawMode) { showToast('Enter Access Token', 'warning'); return }
    if (toSave && !toSave.startsWith('eyJ')) { showToast('Token must start with eyJ', 'warning'); return }
    setSaving(true)
    try {
      await api.updateCookie('gradchoice', toSave)
      showToast('Access Token saved'); loadSettings()
    } catch (e: any) { showToast(e.message || 'Save failed', 'error') }
    finally { setSaving(false) }
  }

  async function handleSaveTavilyKey() {
    if (!tavilyKey.trim()) { showToast('Enter Tavily API Key', 'warning'); return }
    setSaving(true)
    try {
      await api.updateTavilyKey(tavilyKey.trim())
      showToast('Tavily API Key saved'); loadSettings()
    } catch (e: any) { showToast(e.message || 'Save failed', 'error') }
    finally { setSaving(false) }
  }

  async function handleCheckTavily() {
    setCheckingTavily(true); setTavilyResult(null)
    try {
      const r = await api.checkTavily()
      setTavilyResult(r)
      showToast(r.available ? 'Tavily reachable' : 'Tavily unreachable', r.available ? 'success' : 'warning')
      loadSettings()
    } catch (e: any) {
      setTavilyResult({ available: false, detail: e.message || 'Request failed' })
      showToast('Tavily check failed', 'error')
    } finally { setCheckingTavily(false) }
  }

  async function handleSaveLetpubCookie() {
    if (!letpubCookie.trim()) { showToast('Enter PHPSESSID', 'warning'); return }
    setSaving(true)
    try {
      await api.updateCookie('letpub', letpubCookie.trim())
      showToast('PHPSESSID saved'); loadSettings()
    } catch (e: any) { showToast(e.message || 'Save failed', 'error') }
    finally { setSaving(false) }
  }

  async function handleVerifyLetpub() {
    if (!letpubCookie.trim()) { showToast('Enter PHPSESSID first', 'warning'); return }
    setVerifyingLetpub(true); setLetpubVerifyResult(null)
    try {
      const result = await api.verifyLetpub()
      setLetpubVerifyResult(result)
      showToast(result.valid ? 'PHPSESSID valid' : 'Verification failed', result.valid ? 'success' : 'error')
    } catch (e: any) {
      setLetpubVerifyResult({ valid: false, detail: e.message || 'Request failed' })
      showToast('Verify request failed', 'error')
    } finally { setVerifyingLetpub(false) }
  }

  async function handleTogglePlatform(platform: string, enabled: boolean) {
    try {
      await api.togglePlatform(platform, enabled)
      showToast(`${platform} ${enabled ? 'on' : 'off'}`); loadSettings()
    } catch (e: any) { showToast(e.message || 'Failed', 'error') }
  }

  function addCustomField() {
    const newKey = `custom_${customKeys.length + 1}`
    setCustomKeys(prev => [...prev, newKey])
    setCustomValues(prev => ({ ...prev, [newKey]: '' }))
  }

  function removeCustomField(k: string) {
    setCustomKeys(prev => prev.filter(x => x !== k))
    setCustomValues(prev => { const copy = { ...prev }; delete copy[k]; return copy })
  }

  // ─── Tavily Status ────────────────────────────────────
  const tavilyStatus = settings?.tavily_available ? 'CONNECTED' : settings?.tavily_configured ? 'OFFLINE' : 'NO KEY'
  const tavilyStatusColor = settings?.tavily_available ? '#4AFF91' : settings?.tavily_configured ? '#FFB020' : '#666'

  // ─── Render ──────────────────────────────────────────────
  return (
    <div className="page-container" style={{ maxWidth: '800px', paddingTop: '8px' }}>
      <div style={{ marginBottom: '28px' }}>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700,
          background: 'linear-gradient(135deg, #00D4FF, #B088F9)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>CONFIGURATION</h2>
        <p style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '13px' }}>
          Manage API keys, authentication, and data sources.
        </p>
      </div>

      {/* ===== Section 1: DeepSeek ===== */}
      <Section icon="&#x1F916;" title="DeepSeek API Configuration"
        badge={settings?.deepseek_configured ? 'ACTIVE' : undefined}
        defaultOpen={!settings?.deepseek_configured}
      >
        <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
          API Key
        </label>
        <div style={{
          borderRadius: '999px', padding: '2px',
          background: 'linear-gradient(176deg, rgba(176,136,249,.12), rgba(176,136,249,.04))',
          border: '1px solid rgba(176,136,249,.2)',
        }}>
          <input type="password" placeholder="sk-xxxxxxxxxxxxxxxx" value={dsKey}
            onChange={e => setDsKey(e.target.value)}
            style={{
              width: '100%', border: 'none', outline: 'none',
              background: 'rgba(0,0,0,.35)', borderRadius: '999px',
              color: '#E8EDF5', fontSize: '14px', height: '46px',
              paddingLeft: '16px', fontFamily: 'inherit',
            }}
          />
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', margin: '6px 0 14px' }}>
          Get your key at https://platform.deepseek.com/
        </p>
        <Btn color="#B088F9" onClick={handleSaveDeepseek} disabled={saving}>
          Save API Key
        </Btn>
      </Section>

      {/* ===== Section 2: GradChoice Auth ===== */}
      <Section icon="&#x1F511;" title="GradChoice Authentication"
        badge={settings?.gradchoice_cookie_set ? 'CONFIGURED' : undefined}
        defaultOpen={!settings?.gradchoice_cookie_set}
      >
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '16px', lineHeight: 1.6 }}>
          GradChoice uses JWT Bearer Token (not traditional Cookie) for API auth.
          The system sends it as <code style={{
            background: 'rgba(255,255,255,.06)', padding: '1px 6px', borderRadius: '4px', fontSize: '11px', color: '#00D4FF',
          }}>Authorization: Bearer</code>.
        </p>

        {/* Tab Switch */}
        <div style={{
          display: 'flex', marginBottom: '18px',
          background: 'rgba(0,0,0,.25)', borderRadius: '10px', padding: '3px', width: 'fit-content',
        }}>
          <button onClick={() => { setRawMode(false); setRawCookie('') }}
            style={{
              padding: '7px 18px', border: 'none', cursor: 'pointer',
              background: rawMode ? 'transparent' : 'rgba(0,212,255,.15)',
              color: rawMode ? 'var(--text-muted)' : '#00D4FF',
              borderRadius: '7px', fontSize: '13px', fontWeight: 600, fontFamily: 'inherit',
            }}>Structured</button>
          <button onClick={() => { setRawMode(true); setRawCookie(buildCookieString()) }}
            style={{
              padding: '7px 18px', border: 'none', cursor: 'pointer',
              background: rawMode ? 'rgba(255,176,32,.15)' : 'transparent',
              color: rawMode ? '#FFB020' : 'var(--text-muted)',
              borderRadius: '7px', fontSize: '13px', fontWeight: 600, fontFamily: 'inherit',
            }}>Paste Raw</button>
        </div>

        {/* Structured Mode */}
        {!rawMode && (<>
          <div style={{
            background: 'linear-gradient(135deg, rgba(255,176,32,.07), rgba(255,107,53,.04))',
            border: '1px solid rgba(255,176,32,.15)', borderRadius: '10px',
            padding: '14px 18px', marginBottom: '16px', fontSize: '12px', lineHeight: 1.7,
            color: 'var(--text-secondary)',
          }}>
            <strong style={{ color: '#FFB020' }}>How to get:</strong> Open <strong>gradchoice.org</strong> logged in,
            press <kbd style={{ background: 'rgba(0,212,255,.1)', border: '1px solid rgba(0,212,255,.2)', borderRadius: '4px', padding: '1px 5px', fontSize: '11px', color: '#00D4FF' }}>F12</kbd>,
            go to <strong>Console</strong>, run:
            <code style={{
              display: 'block', background: 'rgba(0,0,0,.45)', border: '1px solid rgba(0,212,255,.15)',
              borderRadius: '6px', padding: '8px 12px', margin: '6px 0',
              fontFamily: 'monospace', fontSize: '12px', color: '#00D4FF', cursor: 'pointer',
            }} onClick={(e) => {
              const el = e.currentTarget as HTMLElement
              navigator.clipboard.writeText(el.textContent || '')
              showToast('Copied')
            }}>localStorage.getItem('access_token')</code>
            Copy the output and paste below.
          </div>

          {COOKIE_FIELDS.map(field => (
            <div key={field.key} style={{ marginBottom: '14px' }}>
              <label style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px',
                textTransform: 'uppercase', letterSpacing: '0.5px',
              }}>
                <span style={{ width: '3px', height: '12px', borderRadius: '2px', background: field.color }} />
                {field.label}
                {field.required && <span style={{ color: field.color, fontSize: '11px' }}>*</span>}
              </label>
              <div style={{
                borderRadius: '999px', padding: '2px',
                background: `linear-gradient(176deg, ${field.color}15, ${field.color}05)`,
                border: `1px solid ${field.color}25`,
              }}>
                <input value={cookieFields[field.key]}
                  onChange={e => setCookieFields(prev => ({ ...prev, [field.key]: e.target.value }))}
                  placeholder={field.hint}
                  style={{
                    width: '100%', border: 'none', outline: 'none',
                    background: 'rgba(0,0,0,.35)', borderRadius: '999px',
                    color: '#E8EDF5', fontSize: '14px', height: '44px',
                    paddingLeft: '16px', fontFamily: 'monospace',
                  }}
                />
              </div>
            </div>
          ))}

          {/* Custom Fields */}
          <div style={{ marginTop: '8px', marginBottom: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.5px' }}>CUSTOM FIELDS</span>
              <button onClick={addCustomField} style={{
                background: 'rgba(74,255,145,.08)', border: '1px solid rgba(74,255,145,.2)',
                color: '#4AFF91', borderRadius: '6px', padding: '3px 12px',
                fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
              }}>+ Add</button>
            </div>
            {customKeys.map((k, idx) => (
              <div key={k} style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '6px' }}>
                <input value={k}
                  onChange={e => {
                    const nv = e.target.value
                    setCustomKeys(prev => prev.map((x, i) => i === idx ? nv : x))
                    if (!(nv in customValues)) setCustomValues(prev => ({ ...prev, [nv]: prev[k] || '' }))
                  }}
                  placeholder="key" style={{ width: '120px', outline: 'none',
                    background: 'rgba(0,0,0,.3)', borderRadius: '8px', color: '#B088F9',
                    fontSize: '13px', height: '36px', paddingLeft: '10px', fontFamily: 'monospace',
                    border: '1px solid rgba(176,136,249,.15)',
                  }}
                />
                <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>=</span>
                <input value={customValues[k] || ''}
                  onChange={e => setCustomValues(prev => ({ ...prev, [k]: e.target.value }))}
                  placeholder="value" style={{ flex: 1, outline: 'none',
                    background: 'rgba(0,0,0,.3)', borderRadius: '8px', color: '#E8EDF5',
                    fontSize: '13px', height: '36px', paddingLeft: '10px', fontFamily: 'monospace',
                    border: '1px solid var(--border-color)',
                  }}
                />
                <button onClick={() => removeCustomField(k)} style={{
                  background: 'rgba(255,82,82,.1)', border: '1px solid rgba(255,82,82,.2)',
                  color: '#ff5252', borderRadius: '6px', width: '30px', height: '30px',
                  cursor: 'pointer', fontSize: '13px', fontFamily: 'inherit',
                }}>&#x2715;</button>
              </div>
            ))}
          </div>

          {(() => {
            const preview = buildCookieString()
            if (!preview) return null
            return (
              <div style={{ background: 'rgba(0,0,0,.3)', borderRadius: '8px', border: '1px solid rgba(0,212,255,.1)', marginBottom: '14px', overflow: 'hidden' }}>
                <div style={{ padding: '5px 12px', fontSize: '10px', color: '#00D4FF', borderBottom: '1px solid rgba(0,212,255,.08)', background: 'rgba(0,212,255,.03)' }}>
                  PREVIEW
                </div>
                <pre style={{ margin: 0, padding: '10px 12px', fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', lineHeight: 1.6 }}>
                  {preview}
                </pre>
              </div>
            )
          })()}
        </>)}

        {/* Raw Paste Mode */}
        {rawMode && (<>
          <div style={{
            marginBottom: '12px', borderRadius: '8px',
            background: 'rgba(255,176,32,.06)', border: '1px solid rgba(255,176,32,.15)',
            padding: '10px 14px', fontSize: '12px', color: '#E8C07B', lineHeight: 1.6,
          }}>
            Paste the full JWT token string (starting with <code style={{ background: 'rgba(255,255,255,.06)', padding: '1px 5px', borderRadius: '3px', fontSize: '11px', color: '#FFB020' }}>eyJ</code>).
          </div>
          <textarea value={rawCookie} onChange={e => setRawCookie(e.target.value)} rows={4}
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            style={{ width: '100%', outline: 'none', resize: 'vertical',
              background: 'rgba(0,0,0,.35)', borderRadius: '10px', color: '#E8EDF5',
              fontSize: '13px', lineHeight: 1.7, padding: '12px 14px', fontFamily: 'monospace',
              border: '1px solid rgba(255,176,32,.2)',
            }}
          />
          <div style={{ display: 'flex', gap: '10px', marginTop: '8px', marginBottom: '4px' }}>
            <button onClick={() => parseAndFill(rawCookie)} disabled={!rawCookie.trim()} style={{
              background: 'rgba(0,212,255,.1)', border: '1px solid rgba(0,212,255,.25)',
              color: '#00D4FF', borderRadius: '8px', padding: '6px 14px', fontSize: '12px',
              cursor: rawCookie.trim() ? 'pointer' : 'not-allowed', fontFamily: 'inherit',
              opacity: rawCookie.trim() ? 1 : 0.4,
            }}>Parse to Structured</button>
          </div>
        </>)}

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '8px' }}>
          <Btn color="#FFB020" onClick={handleSaveCookie} disabled={saving}>
            Save Token
          </Btn>
          <Btn color="#00D4FF" onClick={handleVerifyToken} disabled={verifying}>
            Verify Token
          </Btn>
        </div>

        {verifyResult && (
          <div style={{
            marginTop: '12px', borderRadius: '10px', padding: '12px 16px',
            fontSize: '13px', lineHeight: 1.6,
            background: verifyResult.valid ? 'rgba(74,255,145,.06)' : 'rgba(255,82,82,.06)',
            border: verifyResult.valid ? '1px solid rgba(74,255,145,.2)' : '1px solid rgba(255,82,82,.2)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '16px' }}>{verifyResult.valid ? '\u2705' : '\u274C'}</span>
              <strong style={{ color: verifyResult.valid ? '#4AFF91' : '#ff5252' }}>
                {verifyResult.valid ? 'Valid' : 'Invalid'}
              </strong>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{verifyResult.detail}</div>
            {verifyResult.status_code > 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '4px' }}>
                HTTP {verifyResult.status_code} | {verifyResult.url}
              </div>
            )}
          </div>
        )}

        {settings?.gradchoice_cookie_set && (
          <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4AFF91' }}>
            <span>&#x2705;</span> Token persisted to local storage. Survives restart.
          </div>
        )}
      </Section>

      {/* ===== Section 3: Tavily Search API ===== */}
      <Section icon="&#x1F50D;" title="Tavily Search API"
        badge={tavilyStatus}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <span style={{
            width: '10px', height: '10px', borderRadius: '50%',
            background: tavilyStatusColor, boxShadow: `0 0 8px ${tavilyStatusColor}`,
            flexShrink: 0,
          }} />
          <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            Status: <strong style={{ color: tavilyStatusColor }}>
              {settings?.tavily_detail || 'Not checked'}
            </strong>
          </span>
        </div>

        <p style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.6, marginBottom: '14px' }}>
          Tavily is an AI-optimized search API with a generous free tier (1,000 searches/month).
          It searches across multiple sites (tieba.baidu.com, zhihu.com, etc.)
          to find advisor reviews beyond GradChoice.
          <br />Get your free key at <a href="https://tavily.com" target="_blank" style={{ color: '#00D4FF' }}>tavily.com</a>.
        </p>

        <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
          API Key
        </label>
        <div style={{
          borderRadius: '999px', padding: '2px', marginBottom: '14px',
          background: 'linear-gradient(176deg, rgba(0,212,255,.12), rgba(0,212,255,.04))',
          border: '1px solid rgba(0,212,255,.2)',
        }}>
          <input type="password" placeholder="tvly-xxxxxxxxxxxxxxxx" value={tavilyKey}
            onChange={e => setTavilyKey(e.target.value)}
            style={{
              width: '100%', border: 'none', outline: 'none',
              background: 'rgba(0,0,0,.35)', borderRadius: '999px',
              color: '#E8EDF5', fontSize: '14px', height: '44px',
              paddingLeft: '16px', fontFamily: 'inherit',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
          <Btn color="#B088F9" onClick={handleSaveTavilyKey} disabled={saving}>
            Save Key
          </Btn>
          <Btn color="#00D4FF" onClick={handleCheckTavily} disabled={checkingTavily}>
            {checkingTavily ? 'Checking...' : 'Check Connectivity'}
          </Btn>
          {tavilyResult && (
            <span style={{
              fontSize: '13px', color: tavilyResult.available ? '#4AFF91' : '#FFB020',
              fontWeight: 600,
            }}>
              {tavilyResult.available ? 'REACHABLE' : 'UNREACHABLE'}
            </span>
          )}
        </div>
        {tavilyResult && (
          <div style={{
            marginTop: '10px', fontSize: '12px', color: 'var(--text-muted)',
            background: 'rgba(0,0,0,.2)', borderRadius: '8px', padding: '10px 14px',
            border: `1px solid ${tavilyResult.available ? 'rgba(74,255,145,.15)' : 'rgba(255,176,32,.15)'}`,
          }}>
            {tavilyResult.detail}
          </div>
        )}
      </Section>

      {/* ===== Section 3.5: LetPub Authentication ===== */}
      <Section icon="&#x1F4CB;" title="LetPub Authentication (PHPSESSID)"
        badge={settings?.letpub_cookie_set ? 'CONFIGURED' : undefined}
        defaultOpen={!settings?.letpub_cookie_set}
      >
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '16px', lineHeight: 1.6 }}>
          LetPub uses PHP Session-based auth. Only <code style={{
            background: 'rgba(255,255,255,.06)', padding: '1px 6px', borderRadius: '4px', fontSize: '11px', color: '#00D4FF',
          }}>PHPSESSID</code> cookie is required for NSFC grant search.
        </p>

        <div style={{
          background: 'rgba(255,176,32,.06)', border: '1px solid rgba(255,176,32,.15)',
          borderRadius: '8px', padding: '12px 16px', marginBottom: '16px',
          fontSize: '12px', color: '#E8C07B', lineHeight: 1.7,
        }}>
          <strong>How to get:</strong>
          <ol style={{ margin: '6px 0 0 16px', padding: 0 }}>
            <li>Open <a href="https://www.letpub.com.cn/index.php?page=login" target="_blank" style={{ color: '#00D4FF' }}>letpub.com.cn</a> and log in</li>
            <li>F12 → Application → Cookies → www.letpub.com.cn</li>
            <li>Copy the <code style={{ background: 'rgba(255,255,255,.06)', padding: '1px 4px', borderRadius: '3px', color: '#FFB020' }}>PHPSESSID</code> value</li>
            <li>Paste below and click Verify</li>
          </ol>
        </div>

        <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
          PHPSESSID
        </label>
        <div style={{
          borderRadius: '10px', padding: '2px', marginBottom: '14px',
          background: 'linear-gradient(176deg, rgba(255,176,32,.12), rgba(255,176,32,.04))',
          border: '1px solid rgba(255,176,32,.2)',
        }}>
          <input type="text" placeholder="abc123def456..." value={letpubCookie}
            onChange={e => setLetpubCookie(e.target.value)}
            style={{
              width: '100%', border: 'none', outline: 'none',
              background: 'rgba(0,0,0,.35)', borderRadius: '10px',
              color: '#E8EDF5', fontSize: '14px', height: '44px',
              paddingLeft: '16px', fontFamily: 'monospace',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <Btn color="#FFB020" onClick={handleSaveLetpubCookie} disabled={saving}>
            Save PHPSESSID
          </Btn>
          <Btn color="#00D4FF" onClick={handleVerifyLetpub} disabled={verifyingLetpub}>
            {verifyingLetpub ? 'Verifying...' : 'Verify'}
          </Btn>
        </div>

        {letpubVerifyResult && (
          <div style={{
            marginTop: '12px', borderRadius: '10px', padding: '12px 16px',
            fontSize: '13px', lineHeight: 1.6,
            background: letpubVerifyResult.valid ? 'rgba(74,255,145,.06)' : 'rgba(255,82,82,.06)',
            border: letpubVerifyResult.valid ? '1px solid rgba(74,255,145,.2)' : '1px solid rgba(255,82,82,.2)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px' }}>{letpubVerifyResult.valid ? '\u2705' : '\u274C'}</span>
              <strong style={{ color: letpubVerifyResult.valid ? '#4AFF91' : '#ff5252' }}>
                {letpubVerifyResult.valid ? 'Valid' : 'Invalid'}
              </strong>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px' }}>{letpubVerifyResult.detail}</div>
          </div>
        )}

        {settings?.letpub_cookie_set && (
          <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#4AFF91' }}>
            <span>&#x2705;</span> PHPSESSID persisted. Survives restart.
          </div>
        )}
      </Section>

      {/* ===== Section 4: Platform Management ===== */}
      <Section icon="&#x2699;&#xFE0F;" title="Data Source Management"
        badge={`${settings?.platforms?.filter(p => p.enabled).length ?? 0}/${settings?.platforms?.length ?? 0} ON`}
        defaultOpen
      >
        {!settings?.platforms ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '16px' }}>Loading...</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {settings.platforms.map(p => (
              <div key={p.key} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px', borderRadius: '10px', transition: '.2s',
                background: p.enabled ? 'rgba(74,255,145,.03)' : 'transparent',
                border: `1px solid ${p.enabled ? 'rgba(74,255,145,.08)' : 'var(--border-color)'}`,
                cursor: 'pointer',
              }} onClick={() => handleTogglePlatform(p.key, !p.enabled)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <strong style={{ fontSize: '14px', color: '#E8EDF5' }}>{p.name}</strong>
                  <span style={{
                    background: 'rgba(100,130,180,.08)', color: 'var(--text-muted)',
                    fontSize: '11px', padding: '2px 7px', borderRadius: '4px',
                  }}>Tier {p.tier}</span>
                </div>
                <span style={{
                  width: '22px', height: '22px', borderRadius: '6px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: p.enabled ? '#4AFF91' : 'rgba(120,130,150,.25)',
                  color: p.enabled ? '#000' : 'transparent',
                  fontSize: '14px', fontWeight: 700,
                  transition: '.2s',
                  boxShadow: p.enabled ? '0 0 10px rgba(74,255,145,.3)' : 'none',
                }}>
                  {p.enabled ? '\u2713' : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Bottom Nav */}
      <div style={{ textAlign: 'center', paddingBottom: '48px', display: 'flex', gap: '12px', justifyContent: 'center' }}>
        <Link to="/" style={{ textDecoration: 'none' }}>
          <Btn color="#00D4FF">Home</Btn>
        </Link>
        <Link to="/search" style={{ textDecoration: 'none' }}>
          <Btn color="#4AFF91">Search</Btn>
        </Link>
        <Link to="/history" style={{ textDecoration: 'none' }}>
          <Btn color="#B088F9">History</Btn>
        </Link>
      </div>
    </div>
  )
}
