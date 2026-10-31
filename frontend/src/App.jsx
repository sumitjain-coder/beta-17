import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Today from './pages/Today'
import Planner from './pages/Planner'
import Stock from './pages/Stock'
import Recipes from './pages/Recipes'
import Shopping from './pages/Shopping'
import Audit from './pages/Audit'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Today />} />
        <Route path="/planner" element={<Planner />} />
        <Route path="/stock" element={<Stock />} />
        <Route path="/recipes" element={<Recipes />} />
        <Route path="/shopping" element={<Shopping />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="*" element={<p className="text-stone-600">Page not found.</p>} />
      </Route>
    </Routes>
  )
}
