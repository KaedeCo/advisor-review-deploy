import ReactECharts from 'echarts-for-react'
import type { DimensionScores } from '../services/api'

interface Props {
  data: DimensionScores
}

const DIM_LABELS: Record<string, { cn: string; full: string }> = {
  academic:     { cn: '学术水平', full: 'Academic' },
  mentorship:   { cn: '指导风格', full: 'Mentorship' },
  ethics:       { cn: '人品师德', full: 'Ethics' },
  relationship: { cn: '师生关系', full: 'Relationship' },
  funding:      { cn: '科研经费', full: 'Funding' },
  career:       { cn: '学生出路', full: 'Career' },
}

const DIM_KEYS = ['academic', 'mentorship', 'ethics', 'relationship', 'funding', 'career'] as const

/**
 * 暗色主题六维雷达图
 * 展示学术水平、指导风格、人品师德、师生关系、科研经费、学生出路六维评分
 */
export default function RadarChart({ data }: Props) {
  const indicator = DIM_KEYS.map(key => {
    const label = DIM_LABELS[key]
    const score = data[key]?.score ?? 5
    return {
      name: `${label.cn}\n(${score.toFixed(1)})`,
      max: 10,
    }
  })

  const values = DIM_KEYS.map(k => data[k]?.score ?? 5)

  const option = {
    title: {
      text: 'SIX-DIMENSION RADAR',
      subtext: [
        `Overall: ${data.overall.toFixed(1)} / 10`,
        `Confidence: ${(data.confidence * 100).toFixed(0)}%`,
      ].join('  |  '),
      left: 'center',
      textStyle: {
        fontSize: 16, fontWeight: 600, color: '#E8EDF5',
        letterSpacing: '1px',
      },
      subtextStyle: { fontSize: 12, color: '#64748B' },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(17,24,39,.95)',
      borderColor: 'rgba(0,212,255,.2)',
      textStyle: { color: '#E8EDF5', fontSize: 13 },
      formatter: (params: any) => {
        const dimKey = DIM_KEYS[params.dataIndex]
        const dimData = data[dimKey]
        if (!dimData) return params.name
        return `
          <div style="max-width:300px;line-height:1.6">
            <b style="font-size:15px;color:#00D4FF">${DIM_LABELS[dimKey].cn}</b>
            <span style="float:right;font-size:20px;font-weight:900;color:#4AFF91">${dimData.score.toFixed(1)}</span>
            <hr style="border-color:rgba(100,130,180,.2);margin:6px 0">
            <p style="color:#94A3B8;margin:4px 0">${dimData.reasoning || '—'}</p>
            ${
              dimData.red_flags?.length
                ? `<p style="color:#FF6B35;margin:6px 0 0">🚨 ${dimData.red_flags.join(' · ')}</p>`
                : ''
            }
          </div>
        `
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#64748B', fontSize: 12 },
      data: ['六维评分'],
    },
    radar: {
      center: ['50%', '50%'],
      radius: '65%',
      indicator,
      axisName: {
        color: '#94A3B8',
        fontSize: 12,
        fontWeight: 500,
        formatter: (v: string) => v,
      },
      shape: 'polygon',
      splitNumber: 5,
      axisNameGap: 8,
      splitArea: {
        areaStyle: {
          color: ['rgba(0,212,255,0.02)', 'rgba(0,212,255,0.02)',
                  'rgba(0,212,255,0.04)', 'rgba(0,212,255,0.04)',
                  'rgba(0,212,255,0.06)'],
        },
      },
      axisLine: { lineStyle: { color: 'rgba(100,130,180,.2)' } },
      splitLine: { lineStyle: { color: 'rgba(100,130,180,.15)' } },
    },
    series: [
      {
        name: '六维评分',
        type: 'radar',
        data: [
          {
            value: values,
            name: 'Score',
            areaStyle: {
              color: 'rgba(0,212,255,0.15)',
            },
            lineStyle: {
              color: '#00D4FF',
              width: 2,
            },
            itemStyle: {
              color: '#00D4FF',
              borderColor: '#0A1628',
              borderWidth: 2,
            },
            symbol: 'circle',
            symbolSize: 8,
          },
        ],
      },
    ],
    backgroundColor: 'transparent',
  }

  return (
    <div className="glass-card" style={{ padding: '16px', marginBottom: '20px' }}>
      <ReactECharts
        option={option}
        style={{ width: '100%', height: '440px' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  )
}
