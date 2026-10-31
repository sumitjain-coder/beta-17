import { useEffect, useState } from 'react'
import { getHealth, getDbHealth } from '../api'

// Checks the backend every 15 seconds and shows a clear message if something is down.
export default function ServerBanner() {
  const [problem, setProblem] = useState(null)

  useEffect(() => {
    let alive = true
    async function check() {
      try {
        await getHealth()
      } catch {
        if (alive) setProblem('Cannot reach the server. Please check that the backend is running.')
        return
      }
      try {
        await getDbHealth()
        if (alive) setProblem(null)
      } catch {
        if (alive) setProblem('The server is running but the database is not reachable.')
      }
    }
    check()
    const id = setInterval(check, 15000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  if (!problem) return null
  return (
    <div role="alert" className="bg-red-600 px-4 py-2 text-center text-sm font-medium text-white">
      {problem}
    </div>
  )
}
