import React from 'react';
import { Moon, Sun, Database, ExternalLink, Sparkles, LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface TopBarProps {
  breadcrumbs: string[];
  dbHealthy: boolean;
  onOpenTailor: () => void;
  authEnabled?: boolean;
  onLogout?: () => void;
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  breadcrumbs,
  dbHealthy,
  onOpenTailor,
  authEnabled = false,
  onLogout,
  sidebarOpen = true,
  onToggleSidebar,
}) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-12 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center justify-between px-3 sm:px-4 select-none shrink-0 z-30 print:hidden">
      {/* Left: Sidebar Toggle, Brand Badge & Breadcrumbs */}
      <div className="flex items-center space-x-2.5 min-w-0">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            title={sidebarOpen ? 'Ocultar menú lateral' : 'Mostrar menú lateral'}
            aria-label={sidebarOpen ? 'Ocultar menú lateral' : 'Mostrar menú lateral'}
            className="p-1.5 -ml-1 rounded text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors focus-visible:ring-1 focus-visible:ring-zinc-400 focus-visible:outline-none cursor-pointer"
          >
            {sidebarOpen ? (
              <PanelLeftClose className="w-4 h-4" />
            ) : (
              <PanelLeftOpen className="w-4 h-4" />
            )}
          </button>
        )}

        <div className="flex items-center space-x-1.5 font-mono text-xs font-semibold tracking-tight text-zinc-900 dark:text-zinc-100 shrink-0">
          <span className="w-2 h-2 bg-zinc-900 dark:bg-zinc-100 rounded-xs" />
          <span>juanchito</span>
          <span className="text-zinc-400 font-normal">/</span>
          <span className="text-zinc-500 font-normal">studio</span>
        </div>

        <div className="h-3 w-px bg-zinc-200 dark:border-zinc-800 hidden sm:block" />

        {/* Breadcrumb Path */}
        <nav aria-label="Breadcrumb" className="hidden sm:flex items-center space-x-1.5 text-xs text-zinc-500 font-mono">
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <span className="text-zinc-400">/</span>}
              <span className={idx === breadcrumbs.length - 1 ? 'text-zinc-900 dark:text-zinc-200 font-medium' : ''}>
                {crumb}
              </span>
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Right: Actions, Health, Theme */}
      <div className="flex items-center space-x-3 text-xs">
        <button
          type="button"
          onClick={onOpenTailor}
          className="hidden md:inline-flex items-center space-x-1 px-2.5 py-1 rounded border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 hover:border-zinc-400 dark:hover:border-zinc-700 transition-colors font-mono"
        >
          <Sparkles className="w-3 h-3 text-amber-500" />
          <span>tailor studio</span>
        </button>

        <a
          href="https://resume.lol"
          target="_blank"
          rel="noreferrer"
          className="hidden lg:inline-flex items-center space-x-1 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 font-mono text-[11px]"
        >
          <span>resume.lol</span>
          <ExternalLink className="w-2.5 h-2.5" />
        </a>

        <div className="h-3 w-px bg-zinc-200 dark:border-zinc-800" />

        {/* SQLite Database Status */}
        <div
          className="flex items-center space-x-1.5 font-mono text-[11px] text-zinc-500"
          title={dbHealthy ? 'SQLite profile.db conectada' : 'Error de base de datos'}
        >
          <Database className="w-3 h-3" />
          <span className={`w-1.5 h-1.5 rounded-full ${dbHealthy ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          <span className="hidden sm:inline">profile.db</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          className="p-1.5 rounded text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors focus-visible:ring-1 focus-visible:ring-zinc-400 focus-visible:outline-none"
        >
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </button>

        {/* Logout Button (when Auth Gate is enabled) */}
        {authEnabled && onLogout && (
          <button
            type="button"
            onClick={onLogout}
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
            className="p-1.5 rounded text-zinc-500 hover:text-rose-600 dark:text-zinc-400 dark:hover:text-rose-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors focus-visible:ring-1 focus-visible:ring-zinc-400 focus-visible:outline-none"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </header>
  );
};
