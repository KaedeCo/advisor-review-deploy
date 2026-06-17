import ReactECharts from 'echarts-for-react'
import * as echarts from 'echarts'
import type { SentimentResult } from '../services/api'

interface Props {
  data: SentimentResult
  compact?: boolean
}

/**
 * 暗色主题情感柱状图
 */
export default function SentimentChart({ data, compact = false }: Props) {
  const option = {
    ...(compact ? {} : {
    title: {
      text: 'SENTIMENT DISTRIBUTION',
      subtext: `${data.total_count} reviews analyzed`,
      left: 'center',
      textStyle: {
        fontSize: 16, fontWeight: 600, color: '#E8EDF5',
        letterSpacing: '1px',
      },
      subtextStyle: { fontSize: 12, color: '#64748B' },
    },
    }),
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(0,212,255,.05)' } },
      backgroundColor: 'rgba(17,24,39,.9)',
      borderColor: 'rgba(0,212,255,.2)',
      textStyle: { color: '#E8EDF5' },
      formatter: (params: Array<{ name: string; value: number }>) => {
        const p = params[0]
        const labels: Record<string, string> = {
          '正面': 'Positive (&gt;0.6)',
          '负面': 'Negative (&lt;0.4)',
          '中性': 'Neutral (0.4~0.6)',
        }
        return `<b>${labels[p.name] || p.name}</b><br/>Count: <b>${p.value}</b>`
      },
    },
    grid: { left: compact ? 0 : '10%', right: compact ? 0 : '8%', bottom: compact ? '8%' : '14%', top: compact ? '8%' : '28%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['Positive', 'Neutral', 'Negative'],
      axisLabel: {
        fontSize: 13, fontWeight: 500,
        color: ['#4AFF91', '#94A3B8', '#FF6B35'],
        formatter: (v: string) => v.toUpperCase(),
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(100,130,180,.2)' } },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      name: 'count',
      nameTextStyle: { color: '#64748B' },
      axisLabel: { fontSize: 12, color: '#64748B' },
      splitLine: { lineStyle: { color: 'rgba(100,130,180,.08)', type: 'dashed' } },
    },
    series: [
      {
        type: 'bar',
        data: [
          {
            value: data.positive_count,
            itemStyle: {
              color: new (echarts as any).graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#4AFF91' },
                { offset: 1, color: 'rgba(74,255,145,.3)' },
              ]),
              borderRadius: [6, 6, 0, 0],
            },
          },
          {
            value: data.neutral_count,
            itemStyle: {
              color: new (echarts as any).graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#4A9EFF' },
                { offset: 1, color: 'rgba(74,158,255,.3)' },
              ]),
              borderRadius: [6, 6, 0, 0],
            },
          },
          {
            value: data.negative_count,
            itemStyle: {
              color: new (echarts as any).graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#FF6B35' },
                { offset: 1, color: 'rgba(255,107,53,.3)' },
              ]),
              borderRadius: [6, 6, 0, 0],
            },
          },
        ],
        barWidth: '42%',
        label: {
          show: true, position: 'top', fontSize: 15, fontWeight: 700,
          color: '#E8EDF5',
          formatter: (p: { value: number }) => p.value.toString(),
        },
      },
    ],
    // 暗色背景
    backgroundColor: 'transparent',
  }

  return (
    <div style={{ padding: compact ? '0' : '16px', marginBottom: compact ? '0' : '20px' }}>
      <ReactECharts
        option={option}
        style={{ width: '100%', height: compact ? '220px' : '360px' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  )
}
