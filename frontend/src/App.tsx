// frontend/src/App.tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import HomePage from './pages/home'
import AnalysisPage from './pages/analysis-page'
import ResultPage from './pages/result-page'
import { useMriStore } from './utils/stores/mri-store'
import { useResultStore } from './utils/stores/result-store'

function App() {
  const restoreMriSession = useMriStore((state) => state.restoreFromSession);
  const restoreResultsSession = useResultStore((state) => state.restoreFromSession);

  // Auto-restore session la mount
  useEffect(() => {
    const restoreSessions = async () => {
      try {
        // Restore MRI session first
        await restoreMriSession();

        // Then restore results session
        await restoreResultsSession();

        console.log('[APP] Session restore completed');
      } catch (error) {
        console.warn('[APP] Session restore failed:', error);
      }
    };

    restoreSessions();
  }, [restoreMriSession, restoreResultsSession]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/result" element={<ResultPage />} />
      </Routes>
    </Router>
  )
}

export default App