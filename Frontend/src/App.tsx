import { Routes, Route } from 'react-router-dom'
import { ChatsPage } from '@/pages'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatsPage />} />
    </Routes>
  )
}
