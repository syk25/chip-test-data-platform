import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import Layout from '../components/Layout'

type JobStatus = 'idle' | 'uploading' | 'pending' | 'processing' | 'success' | 'failure'

const STATUS_LABEL: Record<JobStatus, string> = {
  idle: '', uploading: '업로드 중...', pending: '대기 중',
  processing: '파싱 중...', success: '완료', failure: '실패',
}
const STATUS_COLOR: Record<JobStatus, string> = {
  idle: '', uploading: 'text-blue-500', pending: 'text-yellow-500',
  processing: 'text-blue-500', success: 'text-green-600', failure: 'text-red-500',
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<JobStatus>('idle')
  const [jobId, setJobId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // SSE 이벤트 수신
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    const es = new EventSource('/api/v1/events')
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'stdf.parsed' && data.file_id) {
          console.log('SSE:', data)
        }
      } catch {}
    }
    return () => es.close()
  }, [])

  const startPolling = (id: number) => {
    pollRef.current = setInterval(async () => {
      const { status: s } = await api.jobStatus(id)
      if (s === 'success' || s === 'failure') {
        clearInterval(pollRef.current!)
        setStatus(s as JobStatus)
      } else {
        setStatus(s as JobStatus)
      }
    }, 2000)
  }

  const upload = async () => {
    if (!file) return
    setStatus('uploading'); setError('')
    try {
      const res = await api.uploadStdf(file)
      setJobId(res.job_id)
      setStatus('pending')
      startPolling(res.job_id)
    } catch (err: any) {
      setError(err.message || '업로드 실패')
      setStatus('failure')
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f?.name.endsWith('.stdf')) setFile(f)
    else setError('.stdf 파일만 업로드 가능합니다.')
  }

  return (
    <Layout>
      <h2 className="text-xl font-bold mb-6">STDF 파일 업로드</h2>

      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white'}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".stdf" className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f) }} />

        {file ? (
          <div>
            <p className="font-medium text-gray-800">{file.name}</p>
            <p className="text-sm text-gray-400 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        ) : (
          <div>
            <p className="text-gray-400">STDF 파일을 드래그하거나 클릭해서 선택</p>
            <p className="text-xs text-gray-300 mt-2">.stdf 형식만 지원</p>
          </div>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      {file && status === 'idle' && (
        <button onClick={upload}
          className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          업로드
        </button>
      )}

      {status !== 'idle' && (
        <div className="mt-6 bg-white border rounded-xl p-6">
          <div className="flex items-center gap-3">
            {(status === 'uploading' || status === 'pending' || status === 'processing') && (
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            )}
            <div>
              <p className={`font-medium ${STATUS_COLOR[status]}`}>{STATUS_LABEL[status]}</p>
              {jobId && <p className="text-xs text-gray-400 mt-1">Job #{jobId} — 2초마다 상태 폴링 중</p>}
              {status === 'success' && <p className="text-sm text-gray-500 mt-1">파싱 완료. 대시보드에서 결과를 확인하세요.</p>}
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
