import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'

// Global handler: fix broken EVE images
// - /icon fails for blueprints → retry with /bp
// - If /bp also fails or other variant → hide
document.addEventListener('error', (e) => {
  const img = e.target as HTMLImageElement;
  if (img.tagName === 'IMG' && img.src.includes('images.evetech.net')) {
    if (img.src.includes('/icon?') && !img.dataset.retried) {
      img.dataset.retried = '1';
      img.src = img.src.replace('/icon?', '/bp?');
    } else {
      img.style.display = 'none';
    }
  }
}, true);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
