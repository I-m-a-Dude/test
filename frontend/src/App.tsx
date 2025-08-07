import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import HomePage from './pages/home'
import AnalysisPage from './pages/analysis-page'
import ResultPage from './pages/result-page'

function App() {
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