import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { ChatProvider } from '@/context/ChatContext'
import { TtsProvider } from '@/context/TtsContext'
import { App } from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatProvider>
          <TtsProvider>
            <App />
          </TtsProvider>
        </ChatProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
)
