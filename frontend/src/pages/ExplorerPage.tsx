import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, LotDetail, Measurement } from '../api/client'
import Layout from '../components/Layout'

export default function ExplorerPage() {
  const [params] = useSearchParams()
  const lotId = params.get('lot_id') ? Number(params.get('lot_id')) : null
  const [lot, setLot] = useState<LotDetail | null>(null)
  const [selectedWafer, setSelectedWafer] = useState<number | null>(null)
  const [selectedPart, setSelectedPart] = useState<number | null>(null)
  const [measurements, setMeasurements] = useState<Measurement[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!lotId) return
    api.lot(lotId).then(setLot).catch(console.error)
  }, [lotId])

  const loadMeasurements = async (partId: number) => {
    setSelectedPart(partId); setLoading(true)
    try {
      setMeasurements(await api.measurements(partId))
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  return (
    <Layout>
      <h2 className="text-xl font-bold mb-6">데이터 탐색기</h2>

      {!lotId && (
        <p className="text-gray-400">대시보드에서 Lot을 클릭해 탐색을 시작하세요.</p>
      )}

      {lot && (
        <div className="space-y-6">
          {/* Lot 요약 */}
          <div className="bg-white rounded-xl border p-5">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-bold text-lg font-mono">{lot.lot_code}</h3>
                <p className="text-sm text-gray-500">{lot.product_type ?? '—'}</p>
              </div>
              <div className="text-right text-sm">
                <p>Wafer <span className="font-bold">{lot.wafer_count}</span></p>
                <p>Part <span className="font-bold">{lot.total_parts.toLocaleString()}</span></p>
                <p className={`font-bold ${lot.fail_rate > 0.1 ? 'text-red-500' : 'text-green-600'}`}>
                  FAIL {(lot.fail_rate * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          {/* Wafer 목록 */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="px-5 py-3 border-b font-medium text-sm">Wafer 목록</div>
            <div className="divide-y">
              {lot.wafers.map(w => (
                <div key={w.id}
                  className={`px-5 py-3 flex justify-between cursor-pointer hover:bg-gray-50 ${selectedWafer === w.id ? 'bg-blue-50' : ''}`}
                  onClick={() => setSelectedWafer(w.id)}>
                  <span className="font-mono text-sm">{w.wafer_code}</span>
                  <span className="text-sm text-gray-500">
                    {w.total_parts.toLocaleString()} parts &bull;{' '}
                    <span className={w.fail_rate > 0.1 ? 'text-red-500' : 'text-green-600'}>
                      FAIL {(w.fail_rate * 100).toFixed(1)}%
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 측정값 조회 (part_id 직접 입력) */}
          <div className="bg-white rounded-xl border p-5">
            <h4 className="font-medium mb-3 text-sm">측정값 조회</h4>
            <div className="flex gap-2">
              <input
                type="number" placeholder="Part ID 입력"
                className="border rounded-lg px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyDown={e => { if (e.key === 'Enter') loadMeasurements(Number((e.target as HTMLInputElement).value)) }}
              />
              <button
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm"
                onClick={() => { const el = document.querySelector('input[type=number]') as HTMLInputElement; if (el.value) loadMeasurements(Number(el.value)) }}>
                조회
              </button>
            </div>

            {loading && <p className="mt-4 text-gray-400 text-sm">로딩 중...</p>}

            {measurements.length > 0 && (
              <div className="mt-4 overflow-auto max-h-64">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {['테스트명', '단위', '결과', 'PASS', '알람'].map(h => (
                        <th key={h} className="px-3 py-2 text-left font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {measurements.map(m => (
                      <tr key={m.id} className={m.is_alarm ? 'bg-red-50' : ''}>
                        <td className="px-3 py-2">{m.test_name}</td>
                        <td className="px-3 py-2 text-gray-400">{m.unit ?? '—'}</td>
                        <td className="px-3 py-2 font-mono">{m.result?.toFixed(4) ?? '—'}</td>
                        <td className={`px-3 py-2 font-medium ${m.is_pass ? 'text-green-600' : 'text-red-500'}`}>
                          {m.is_pass ? 'PASS' : 'FAIL'}
                        </td>
                        <td className="px-3 py-2">{m.is_alarm ? '⚠️' : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  )
}
