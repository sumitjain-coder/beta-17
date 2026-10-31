import { NavLink, Outlet } from 'react-router-dom'
import ServerBanner from './ServerBanner'

const LINKS = [
  { to: '/', label: 'Today' },
  { to: '/planner', label: 'Planner' },
  { to: '/stock', label: 'Stock' },
  { to: '/recipes', label: 'Recipes' },
  { to: '/shopping', label: 'Shopping' },
  { to: '/audit', label: 'Audit' },
]

export default function Layout() {
  return (
    <div className="min-h-screen">
      <ServerBanner />
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          <span className="text-lg font-bold text-emerald-700">KitchenSync</span>
          <nav className="flex gap-1 overflow-x-auto">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  'whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium ' +
                  (isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-stone-700 hover:bg-stone-100')
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
