import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import ExplorerPage from './pages/ExplorerPage'
import LoginPage from './pages/LoginPage'
import UploadPage from './pages/UploadPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  return localStorage.getItem('token') ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/upload" element={<RequireAuth><UploadPage /></RequireAuth>} />
        <Route path="/explorer" element={<RequireAuth><ExplorerPage /></RequireAuth>} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
