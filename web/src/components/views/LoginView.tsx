import React, { useState } from 'react';
import { Lock, Loader2, AlertCircle, Moon, Sun } from 'lucide-react';
import { api } from '../../services/api';
import { useTheme } from '../../context/ThemeContext';
import type { AuthStatusResponse } from '../../types/profile';

interface LoginViewProps {
  onSuccess: (status: AuthStatusResponse) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onSuccess }) => {
  const { theme, toggleTheme } = useTheme();
  const [username, setUsername] = useState('mateo');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Ingresa la contraseña de acceso.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const status = await api.login(username.trim() || 'mateo', password);
      onSuccess(status);
    } catch (err: any) {
      setError(err.message || 'Credenciales inválidas.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-zinc-100 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans select-none">
      {/* Minimal Top Bar */}
      <header className="h-12 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center justify-between px-4">
        <div className="flex items-center space-x-1.5 font-mono text-xs font-semibold tracking-tight">
          <span className="w-2 h-2 bg-zinc-900 dark:bg-zinc-100 rounded-xs" />
          <span>juanchito</span>
          <span className="text-zinc-400 font-normal">/</span>
          <span className="text-zinc-500 font-normal">auth_gate</span>
        </div>

        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          className="p-1.5 rounded text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </button>
      </header>

      {/* Centered Workbench Auth Form */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-sm bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6">
          <div className="flex items-center space-x-2 mb-1">
            <Lock className="w-4 h-4 text-zinc-500" />
            <h1 className="font-mono text-sm font-semibold tracking-tight">
              Acceso Privado — Juanchito Studio
            </h1>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-6 leading-relaxed">
            Instancia protegida. Ingresa tus credenciales de propietario para acceder al perfil y al motor de adaptación ATS.
          </p>

          {error && (
            <div className="mb-4 p-2.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 font-mono text-[11px] flex items-center space-x-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="login-username"
                className="block font-mono text-[11px] uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1.5"
              >
                Usuario
              </label>
              <input
                id="login-username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-zinc-500 dark:focus:border-zinc-500"
                placeholder="mateo"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block font-mono text-[11px] uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1.5"
              >
                Contraseña
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-zinc-500 dark:focus:border-zinc-500"
                placeholder="••••••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 px-3 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-950 font-mono text-xs font-medium hover:bg-zinc-800 dark:hover:bg-zinc-200 disabled:opacity-50 transition-colors flex items-center justify-center space-x-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>verificando...</span>
                </>
              ) : (
                <span>desbloquear sesión</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
