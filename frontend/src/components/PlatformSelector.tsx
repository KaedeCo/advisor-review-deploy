import { Checkbox } from 'tdesign-react'
import type { Platform } from '../services/api'

interface Props {
  platforms: Platform[]
  selectedKeys: string[]
  onChange: (keys: string[]) => void
}

/**
 * 平台选择器 — 暗色风格
 */
export default function PlatformSelector({ platforms, selectedKeys, onChange }: Props) {
  const handleChange = (value: string[] | number[]) => {
    onChange(value as string[])
  }

  if (!platforms.length) return null

  const tierLabels: Record<number, string> = { 1: '专业评价平台', 2: '社交平台', 3: '学术辅助', 5: '硕博社区' }
  const tiers = [...new Set(platforms.map(p => p.tier))].sort()

  return (
    <div style={{ marginBottom: '20px' }}>
      <Checkbox.Group value={selectedKeys} onChange={handleChange}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {tiers.map(tier => {
            const group = platforms.filter(p => p.tier === tier)
            return (
              <div key={tier}>
                <div style={{
                  fontSize: '12px', color: 'var(--text-muted)',
                  marginBottom: '8px', paddingLeft: '4px',
                  letterSpacing: '1px', textTransform: 'uppercase',
                }}>
                  // {tierLabels[tier] || `Tier ${tier}`}
                </div>
                <FlexWrap>
                  {group.map(p => (
                    <Checkbox
                      key={p.key}
                      value={p.key}
                      style={{ '--td-text-color-primary': '#E8EDF4' } as React.CSSProperties}
                    >
                      <span style={{ fontSize: '14px' }}>{p.name}</span>
                    </Checkbox>
                  ))}
                </FlexWrap>
              </div>
            )
          })}
        </div>
      </Checkbox.Group>
    </div>
  )
}

function FlexWrap({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 24px' }}>
      {children}
    </div>
  )
}
