import { NavLink } from 'react-router-dom'
import Button from './Button'

/**
 * Presentational shell. Nav items and the current user arrive as props;
 * the composition root wires them to auth state.
 */
export default function AppLayout({ user, navItems, onLogout, children }) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-6 px-6">
          <div className="flex items-center gap-8">
            <span className="text-sm font-semibold text-slate-900">Knowledge &amp; Tasks</span>
            <nav className="flex items-center gap-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      isActive ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-900'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-slate-900">{user.email}</p>
              <p className="text-xs capitalize text-slate-500">{user.role}</p>
            </div>
            <Button variant="secondary" onClick={onLogout}>
              Log out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
    </div>
  )
}
