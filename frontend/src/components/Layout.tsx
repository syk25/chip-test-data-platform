import { Link, useNavigate } from 'react-router-dom'

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const logout = () => { localStorage.removeItem('token'); navigate('/login') }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-6">
          <span className="font-bold text-gray-800">Chip Test Data Platform</span>
          <Link to="/dashboard" className="text-sm text-gray-600 hover:text-blue-600">대시보드</Link>
          <Link to="/upload" className="text-sm text-gray-600 hover:text-blue-600">파일 업로드</Link>
          <Link to="/explorer" className="text-sm text-gray-600 hover:text-blue-600">데이터 탐색</Link>
        </div>
        <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">로그아웃</button>
      </nav>
      <main className="max-w-6xl mx-auto p-6">{children}</main>
    </div>
  )
}
