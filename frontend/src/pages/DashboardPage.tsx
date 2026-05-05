import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, LotSummary } from '../api/client'
import Layout from '../components/Layout'

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5 border">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const [lots, setLots] = useState<LotSummary[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.lots().then(setLots).catch(console.error).finally(() => setLoading(false))
  }, [])

  const totalParts = lots.reduce((s, l) => s + l.total_parts, 0)
  const avgFail = lots.length ? (lots.reduce((s, l) => s + l.fail_rate, 0) / lots.length * 100).toFixed(1) : '—'

  return (
    <Layout>
      <h2 className="text-xl font-bold mb-6">대시보드</h2>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="전체 Lot" value={String(lots.length)} />
        <StatCard label="전체 Part" value={totalParts.toLocaleString()} />
        <StatCard label="평균 FAIL률" value={`${avgFail}%`} />
      </div>

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="px-5 py-4 border-b flex justify-between items-center">
          <h3 className="font-medium">Lot 목록</h3>
          <span className="text-sm text-gray-400">{lots.length}개</span>
        </div>

        {loading ? (
          <p className="p-8 text-center text-gray-400">로딩 중...</p>
        ) : lots.length === 0 ? (
          <p className="p-8 text-center text-gray-400">
            Lot이 없습니다.{' '}
            <button className="text-blue-500 underline" onClick={() => navigate('/upload')}>
              STDF 파일을 업로드해보세요.
            </button>
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500">
              <tr>
                {['Lot Code', '제품', 'Wafer', 'Part', 'FAIL률', '등록일'].map(h => (
                  <th key={h} className="px-5 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {lots.map(lot => (
                <tr key={lot.id} className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/explorer?lot_id=${lot.id}`)}>
                  <td className="px-5 py-3 font-mono text-blue-600">{lot.lot_code}</td>
                  <td className="px-5 py-3 text-gray-600">{lot.product_type ?? '—'}</td>
                  <td className="px-5 py-3">{lot.wafer_count}</td>
                  <td className="px-5 py-3">{lot.total_parts.toLocaleString()}</td>
                  <td className="px-5 py-3">
                    <span className={`font-medium ${lot.fail_rate > 0.1 ? 'text-red-500' : 'text-green-600'}`}>
                      {(lot.fail_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-400">{new Date(lot.created_at).toLocaleDateString('ko-KR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  )
}
