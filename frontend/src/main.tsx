import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Note: StrictMode removed to prevent WebSocket double-connection issues in development
createRoot(document.getElementById('root')!).render(
  <App />,
)

