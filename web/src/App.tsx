import React, { useEffect, useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { TopBar } from './components/TopBar';
import { Sidebar } from './components/Sidebar';
import type { NavigationTarget } from './components/Sidebar';
import { PersonalHeaderCanvas } from './components/views/PersonalHeaderCanvas';
import { CompanyCanvas } from './components/views/CompanyCanvas';
import { NewCompanyCanvas } from './components/views/NewCompanyCanvas';
import { ReposCanvas } from './components/views/ReposCanvas';
import { SkillsCanvas } from './components/views/SkillsCanvas';
import { CertsCanvas } from './components/views/CertsCanvas';
import { TailoringStudioCanvas } from './components/views/TailoringStudioCanvas';
import { HistoryCanvas } from './components/views/HistoryCanvas';
import type { FullProfileData, WorkExperience } from './types/profile';
import { api } from './services/api';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';

export const WorkbenchApp: React.FC = () => {
  const [profile, setProfile] = useState<FullProfileData | null>(null);
  const [historyCount, setHistoryCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dbHealthy, setDbHealthy] = useState(true);

  // Navigation State
  const [nav, setNav] = useState<NavigationTarget>({ view: 'personal' });
  const [isCreatingCompany, setIsCreatingCompany] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, historyItems] = await Promise.all([
        api.getProfile(),
        api.getResumeHistory().catch(() => []),
      ]);
      setProfile(data);
      setHistoryCount(historyItems.length);
      setDbHealthy(true);

      // Si estábamos en una experiencia que ya no existe o es la primera carga y no hay exp seleccionada
      if (data.experiences && data.experiences.length > 0) {
        setNav((prev) => {
          if (prev.view === 'experience' && !prev.expId) {
            return { view: 'experience', expId: data.experiences[0].id };
          }
          return prev;
        });
      }
    } catch (err: any) {
      setError(err.message || 'No se pudo conectar con el backend de FastAPI');
      setDbHealthy(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute breadcrumbs
  const getBreadcrumbs = (): string[] => {
    if (!profile) return ['profile.db'];
    if (nav.view === 'personal') return ['profile.db', 'header_variables'];
    if (nav.view === 'repos') return ['profile.db', 'tracked_repositories'];
    if (nav.view === 'skills') return ['profile.db', 'skill_matrix'];
    if (nav.view === 'certs') return ['profile.db', 'certifications'];
    if (nav.view === 'history') return ['archive', 'generated_resumes'];
    if (nav.view === 'tailor') return ['studio', 'tailor', 'ats_optimizer'];
    if (nav.view === 'experience') {
      if (isCreatingCompany) return ['profile.db', 'experiences', 'new_company'];
      const exp = profile.experiences.find((e) => e.id === nav.expId);
      return ['profile.db', 'experiences', exp ? exp.company.toLowerCase().replace(/\s+/g, '_') : 'overview'];
    }
    return ['profile.db'];
  };

  // Find currently selected experience
  const currentExp: WorkExperience | undefined =
    nav.view === 'experience' && nav.expId
      ? profile?.experiences.find((e) => e.id === nav.expId)
      : profile?.experiences[0];

  const handleStartNewCompany = () => {
    setIsCreatingCompany(true);
    setNav({ view: 'experience' });
  };

  const handleDeleteCompany = async (id: number) => {
    const exp = profile?.experiences.find((e) => e.id === id);
    if (!confirm(`¿Eliminar la empresa "${exp?.company}" y sus iniciativas?`)) return;
    try {
      await api.deleteExperience(id);
      await loadData();
      if (profile && profile.experiences.length > 1) {
        const nextExp = profile.experiences.find((e) => e.id !== id);
        setNav({ view: 'experience', expId: nextExp?.id });
      } else {
        setNav({ view: 'personal' });
      }
    } catch (err: any) {
      alert(err.message || 'Error al eliminar');
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-zinc-100 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans">
      {/* Top Engineering Bar */}
      <TopBar
        breadcrumbs={getBreadcrumbs()}
        dbHealthy={dbHealthy}
        onOpenTailor={() => {
          setIsCreatingCompany(false);
          setNav({ view: 'tailor' });
        }}
      />

      {/* Main Workbench Body: Sidebar + Editor Canvas */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          currentNav={nav}
          onNavigate={(target) => {
            setIsCreatingCompany(false);
            setNav(target);
          }}
          experiences={profile?.experiences || []}
          repoCount={profile?.tracked_repos.length || 0}
          activeRepoCount={profile?.tracked_repos.filter((r) => r.is_active).length || 0}
          skillCategoryCount={profile?.skills.length || 0}
          certCount={profile?.certifications.length || 0}
          historyCount={historyCount}
          onNewCompany={handleStartNewCompany}
        />

        {/* Central Editor Canvas */}
        <main className="flex-1 overflow-y-auto bg-zinc-50 dark:bg-zinc-950/40">
          {loading && (
            <div className="flex flex-col items-center justify-center h-full text-zinc-400 space-y-2 font-mono text-xs">
              <Loader2 className="w-5 h-5 animate-spin text-zinc-600 dark:text-zinc-400" />
              <span>reading profile.db...</span>
            </div>
          )}

          {error && !loading && (
            <div className="max-w-lg mx-auto my-16 p-4 rounded bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 font-mono text-xs">
              <div className="flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold mb-1">Database connection failed</p>
                  <p className="text-[11px] leading-relaxed mb-3">{error}</p>
                  <button
                    type="button"
                    onClick={loadData}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-600 text-white hover:bg-rose-700"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>retry</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {!loading && profile && (
            <div className="h-full">
              {nav.view === 'personal' && (
                <PersonalHeaderCanvas
                  personal={profile.personal}
                  onUpdate={(updated) =>
                    setProfile((prev) => (prev ? { ...prev, personal: updated } : null))
                  }
                />
              )}

              {nav.view === 'experience' && (
                <>
                  {isCreatingCompany ? (
                    <NewCompanyCanvas
                      onSuccess={(newExpId) => {
                        setIsCreatingCompany(false);
                        loadData().then(() => {
                          setNav({ view: 'experience', expId: newExpId });
                        });
                      }}
                      onCancel={() => {
                        setIsCreatingCompany(false);
                        if (profile.experiences.length > 0) {
                          setNav({ view: 'experience', expId: profile.experiences[0].id });
                        } else {
                          setNav({ view: 'personal' });
                        }
                      }}
                    />
                  ) : currentExp ? (
                    <CompanyCanvas
                      key={currentExp.id}
                      experience={currentExp}
                      onReload={loadData}
                      onDeleteCompany={handleDeleteCompany}
                    />
                  ) : (
                    <div className="text-center py-20 font-mono text-xs text-zinc-400">
                      <span>No hay empresas registradas.</span>{' '}
                      <button
                        type="button"
                        onClick={handleStartNewCompany}
                        className="underline text-zinc-900 dark:text-zinc-100 ml-1 font-semibold"
                      >
                        Crear una ahora
                      </button>
                    </div>
                  )}
                </>
              )}

              {nav.view === 'repos' && (
                <ReposCanvas
                  repos={profile.tracked_repos}
                  githubUser={profile.personal.github}
                  onReload={loadData}
                />
              )}

              {nav.view === 'skills' && (
                <SkillsCanvas
                  skills={profile.skills}
                  onReload={loadData}
                />
              )}

              {nav.view === 'certs' && (
                <CertsCanvas
                  certifications={profile.certifications}
                  onReload={loadData}
                />
              )}

              {nav.view === 'tailor' && <TailoringStudioCanvas />}

              {nav.view === 'history' && (
                <HistoryCanvas onNavigateToStudio={() => setNav({ view: 'tailor' })} />
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <ThemeProvider>
      <WorkbenchApp />
    </ThemeProvider>
  );
}
