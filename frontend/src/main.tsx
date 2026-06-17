import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'tdesign-react'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        brandColor: '#00D4FF',
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
