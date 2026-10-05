import React, { useEffect, useState, useMemo } from 'react';
import {
  Search,
  Printer,
  Download,
  Copy,
  Check,
  FileText,
  Clock,
  Sparkles,
  Columns,
  Eye,
  Code,
  Loader2,
  AlertCircle,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../../services/api';
import type { ResumeHistoryItem, ResumeHistoryDetail } from '../../types/profile';
import { LiveResumePreview } from './LiveResumePreview';
import { ScorecardView } from './ScorecardView';

interface HistoryCanvasProps {
  onNavigateToStudio?: () => void;
}

export const HistoryCanvas: React.FC<HistoryCanvasProps> = ({ onNavigateToStudio }) => {
  const [historyList, setHistoryList] = useState<ResumeHistoryItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedFilename, setSelectedFilename] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<ResumeHistoryDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [languageFilter, setLanguageFilter] = useState<'all' | 'en' | 'es'>('all');

  // UI Tabs & View Mode
  const [activeTab, setActiveTab] = useState<'cv' | 'ats'>('cv');
  const [viewMode, setViewMode] = useState<'split' | 'preview' | 'markdown'>('split');
  const [copied, setCopied] = useState(false);

  // Auditing state
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  // Load history list
  const loadHistory = async (autoSelectFirst = true) => {
    setLoadingList(true);
    setListError(null);
    try {
      const items = await api.getResumeHistory();
      setHistoryList(items);

      if (items.length > 0 && autoSelectFirst) {
        setSelectedFilename((prev) => {
          if (prev && items.some((it) => it.filename === prev)) {
            return prev;
          }
          return items[0].filename;
        });
      }
    } catch (err: any) {
      setListError(err.message || 'Error al cargar el historial de currículums');
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadHistory(true);
  }, []);

  // When selected filename changes, fetch detail
  useEffect(() => {
    if (!selectedFilename) {
      setSelectedDetail(null);
      return;
    }

    let isMounted = true;
    const fetchDetail = async () => {
      setLoadingDetail(true);
      setDetailError(null);
      try {
        const detail = await api.getResumeHistoryDetail(selectedFilename);
        if (isMounted) {
          setSelectedDetail(detail);
        }
      } catch (err: any) {
        if (isMounted) {
          setDetailError(err.message || 'Error al cargar el detalle del currículum');
        }
      } finally {
        if (isMounted) {
          setLoadingDetail(false);
        }
      }
    };

    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedFilename]);

  // Filtered items
  const filteredItems = useMemo(() => {
    return historyList.filter((item) => {
      const matchesLang = languageFilter === 'all' || item.language === languageFilter;
      const query = searchQuery.toLowerCase().trim();
      if (!query) return matchesLang;

      const matchesText =
        item.company.toLowerCase().includes(query) ||
        item.role.toLowerCase().includes(query) ||
        (item.headline && item.headline.toLowerCase().includes(query)) ||
        item.filename.toLowerCase().includes(query);

      return matchesLang && matchesText;
    });
  }, [historyList, searchQuery, languageFilter]);

  // On-demand ATS Audit
  const handleRunAudit = async () => {
    if (!selectedFilename) return;
    setIsAuditing(true);
    setAuditError(null);
    try {
      const updated = await api.auditResumeHistory(selectedFilename);
      setSelectedDetail(updated);

      // Actualizar la lista en memoria para reflejar el nuevo puntaje
      setHistoryList((prev) =>
        prev.map((it) =>
          it.filename === selectedFilename
            ? { ...it, ats_score: updated.ats_score, ats_decision: updated.ats_decision }
            : it
        )
      );
    } catch (err: any) {
      setAuditError(err.message || 'Error durante la auditoría ATS con IA.');
    } finally {
      setIsAuditing(false);
    }
  };

  // PDF Export
  const handlePrintPdf = () => {
    if (!selectedDetail) return;
    const originalTitle = document.title;
    const company = selectedDetail.company.replace(/[^\w-]/g, '_') || 'company';
    const role = selectedDetail.role.replace(/[^\w-]/g, '_') || 'role';
    const lang = selectedDetail.language || 'en';

    document.title = `resume_${company}_${role}_${lang}`;
    window.print();

    setTimeout(() => {
      document.title = originalTitle;
    }, 1000);
  };

  // Download Markdown
  const handleDownloadMarkdown = () => {
    if (!selectedDetail) return;
    const blob = new Blob([selectedDetail.markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedDetail.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Copy Markdown
  const handleCopyMarkdown = async () => {
    if (!selectedDetail) return;
    try {
      await navigator.clipboard.writeText(selectedDetail.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Error copying to clipboard:', err);
    }
  };

  return (
    <div className="h-full flex overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Left Master Pane: Search and List */}
      <div className="w-80 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col shrink-0 overflow-hidden print:hidden">
        {/* Search & Filters Header */}
        <div className="p-3 border-b border-zinc-200 dark:border-zinc-800 space-y-2 bg-zinc-50/50 dark:bg-zinc-900/50">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-500">
              Historial de CVs ({historyList.length})
            </span>
            <button
              type="button"
              onClick={() => loadHistory(false)}
              className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 p-1 rounded"
              title="Recargar historial"
            >
              <RefreshCw className={`w-3 h-3 ${loadingList ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-zinc-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por empresa o rol..."
              className="w-full pl-8 pr-3 py-1 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded text-xs text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-hidden focus:border-zinc-400 dark:focus:border-zinc-600"
            />
          </div>

          {/* Language Filter Pills */}
          <div className="flex items-center space-x-1 pt-0.5">
            <span className="text-[10px] text-zinc-400 font-mono mr-1">Idioma:</span>
            {(['all', 'en', 'es'] as const).map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => setLanguageFilter(lang)}
                className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-medium transition-colors ${
                  languageFilter === lang
                    ? 'bg-zinc-800 dark:bg-zinc-200 text-white dark:text-zinc-900'
                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                }`}
              >
                {lang === 'all' ? 'Todos' : lang}
              </button>
            ))}
          </div>
        </div>

        {/* List of Resumes */}
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-200/60 dark:divide-zinc-800/60">
          {loadingList && historyList.length === 0 && (
            <div className="flex flex-col items-center justify-center h-48 text-zinc-400 space-y-2 font-mono text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-zinc-500" />
              <span>Cargando historial...</span>
            </div>
          )}

          {listError && (
            <div className="p-4 text-rose-600 dark:text-rose-400 font-mono text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{listError}</span>
            </div>
          )}

          {!loadingList && filteredItems.length === 0 && (
            <div className="p-8 text-center text-zinc-400 font-mono text-xs space-y-3">
              <FileText className="w-8 h-8 mx-auto text-zinc-300 dark:text-zinc-700" />
              <p>No se encontraron currículums generados.</p>
              {onNavigateToStudio && (
                <button
                  type="button"
                  onClick={onNavigateToStudio}
                  className="inline-flex items-center space-x-1 px-3 py-1 rounded bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-sans font-medium"
                >
                  <Sparkles className="w-3 h-3 text-amber-400" />
                  <span>Crear uno en Studio</span>
                </button>
              )}
            </div>
          )}

          {filteredItems.map((item) => {
            const isSelected = selectedFilename === item.filename;
            const hasAtsScore = item.ats_score !== undefined && item.ats_score !== null;
            const isApproved = hasAtsScore && item.ats_score! >= 85;

            return (
              <button
                key={item.filename}
                type="button"
                onClick={() => setSelectedFilename(item.filename)}
                className={`w-full text-left p-3 transition-colors flex flex-col space-y-1.5 ${
                  isSelected
                    ? 'bg-zinc-100 dark:bg-zinc-800/90 border-l-2 border-emerald-600 dark:border-emerald-400'
                    : 'hover:bg-zinc-50 dark:hover:bg-zinc-900/60'
                }`}
              >
                {/* Company, Score and Language */}
                <div className="flex items-center justify-between gap-1">
                  <span className="font-semibold text-xs text-zinc-900 dark:text-zinc-100 truncate">
                    {item.company}
                  </span>

                  <div className="flex items-center space-x-1 shrink-0">
                    {/* ATS Score Badge */}
                    {hasAtsScore ? (
                      <span
                        className={`font-mono text-[9px] px-1.5 py-0.2 rounded font-bold ${
                          isApproved
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300'
                        }`}
                        title={`Puntaje ATS: ${item.ats_score}/100`}
                      >
                        {item.ats_score} pts
                      </span>
                    ) : (
                      <span className="font-mono text-[9px] px-1.5 py-0.2 rounded bg-zinc-200/60 dark:bg-zinc-800 text-zinc-400">
                        Sin auditar
                      </span>
                    )}

                    {/* Language Badge */}
                    <span
                      className={`font-mono text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                        item.language === 'es'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                          : 'bg-sky-100 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300'
                      }`}
                    >
                      {item.language}
                    </span>
                  </div>
                </div>

                {/* Role */}
                <p className="text-xs text-zinc-600 dark:text-zinc-400 truncate font-medium">
                  {item.role}
                </p>

                {/* Headline snippet if present */}
                {item.headline && (
                  <p className="text-[11px] text-zinc-400 dark:text-zinc-500 truncate italic">
                    {item.headline}
                  </p>
                )}

                {/* Footer metadata */}
                <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 pt-0.5">
                  <span className="flex items-center space-x-1">
                    <Clock className="w-2.5 h-2.5 text-zinc-400" />
                    <span>{item.created_at}</span>
                  </span>
                  <span>{item.word_count} w</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right Detail Pane: View & Action Hub */}
      <div className="flex-1 flex flex-col overflow-hidden bg-zinc-100 dark:bg-zinc-950">
        {loadingDetail && (
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 font-mono text-xs space-y-2">
            <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
            <span>Cargando currículum...</span>
          </div>
        )}

        {detailError && !loadingDetail && (
          <div className="p-8 max-w-md mx-auto my-auto bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded p-4 text-xs font-mono text-rose-800 dark:text-rose-300">
            <p className="font-semibold mb-1">Error al abrir currículum</p>
            <p>{detailError}</p>
          </div>
        )}

        {!selectedFilename && !loadingList && (
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 font-mono text-xs p-8 text-center space-y-2">
            <FileText className="w-10 h-10 text-zinc-300 dark:text-zinc-700" />
            <p>Selecciona un currículum del panel izquierdo para previsualizarlo o descargarlo.</p>
          </div>
        )}

        {selectedDetail && !loadingDetail && (
          <>
            {/* Top Engineering Toolbar for Selected Resume */}
            <div className="p-3 sm:px-5 sm:py-3 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shrink-0 flex flex-wrap items-center justify-between gap-3 print:hidden">
              {/* Company, Role & ATS Score Summary */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center space-x-2">
                  <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate">
                    {selectedDetail.company}
                  </h2>
                  <span
                    className={`font-mono text-[9px] px-1.5 py-0.2 rounded font-bold uppercase shrink-0 ${
                      selectedDetail.language === 'es'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                        : 'bg-sky-100 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300'
                    }`}
                  >
                    {selectedDetail.language}
                  </span>

                  {selectedDetail.ats_score !== undefined && selectedDetail.ats_score !== null ? (
                    <span
                      className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold ${
                        selectedDetail.ats_score >= 85
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300'
                      }`}
                    >
                      {selectedDetail.ats_score}/100 ATS
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-400">
                      Sin auditar
                    </span>
                  )}

                  <span className="text-[11px] font-mono text-zinc-400 truncate">
                    {selectedDetail.created_at}
                  </span>
                </div>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 truncate">
                  {selectedDetail.role}
                </p>
              </div>

              {/* Main Tab Switcher: [ Currículum | Auditoría ATS ] */}
              <div className="flex items-center bg-zinc-100 dark:bg-zinc-800 p-0.5 rounded border border-zinc-200 dark:border-zinc-700">
                <button
                  type="button"
                  onClick={() => setActiveTab('cv')}
                  className={`px-2.5 py-1 rounded text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer ${
                    activeTab === 'cv'
                      ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Currículum</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('ats')}
                  className={`px-2.5 py-1 rounded text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer ${
                    activeTab === 'ats'
                      ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Auditoría ATS</span>
                  {selectedDetail.ats_score !== undefined && selectedDetail.ats_score !== null && (
                    <span className="font-mono text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                      ({selectedDetail.ats_score})
                    </span>
                  )}
                </button>
              </div>

              {/* Context Actions for Currículum */}
              {activeTab === 'cv' && (
                <>
                  {/* View Mode Switcher */}
                  <div className="flex items-center bg-zinc-100 dark:bg-zinc-800 p-0.5 rounded border border-zinc-200 dark:border-zinc-700">
                    <button
                      type="button"
                      onClick={() => setViewMode('split')}
                      className={`px-2 py-1 rounded text-xs font-medium flex items-center space-x-1 transition-colors cursor-pointer ${
                        viewMode === 'split'
                          ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-xs'
                          : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                      }`}
                      title="Vista dividida (Editor y Preview)"
                    >
                      <Columns className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Split</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('preview')}
                      className={`px-2 py-1 rounded text-xs font-medium flex items-center space-x-1 transition-colors cursor-pointer ${
                        viewMode === 'preview'
                          ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-xs'
                          : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                      }`}
                      title="Vista previa completa hoja A4"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">A4</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('markdown')}
                      className={`px-2 py-1 rounded text-xs font-medium flex items-center space-x-1 transition-colors cursor-pointer ${
                        viewMode === 'markdown'
                          ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-xs'
                          : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                      }`}
                      title="Código Markdown crudo"
                    >
                      <Code className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">MD</span>
                    </button>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={handleCopyMarkdown}
                      title="Copiar Markdown al portapapeles"
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                          <span className="text-emerald-500">¡Copiado!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copiar MD</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={handleDownloadMarkdown}
                      title="Descargar archivo .md"
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>.md</span>
                    </button>

                    <button
                      type="button"
                      onClick={handlePrintPdf}
                      title="Exportar / Imprimir currículum en PDF vectorial de 1 página"
                      className="inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium border border-emerald-600 dark:border-emerald-500 bg-emerald-600 dark:bg-emerald-500 text-white hover:bg-emerald-700 dark:hover:bg-emerald-600 transition-colors shadow-xs cursor-pointer"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      <span>Descargar PDF</span>
                    </button>
                  </div>
                </>
              )}

              {/* Context Actions for ATS Audit */}
              {activeTab === 'ats' && (
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={handleRunAudit}
                    disabled={isAuditing}
                    className="inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isAuditing ? 'animate-spin' : ''}`} />
                    <span>{selectedDetail.evaluation ? 'Re-auditar con IA' : 'Auditar ATS ahora'}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Content View Body */}
            {activeTab === 'cv' ? (
              <div className="flex-1 flex overflow-hidden print:overflow-visible print:block">
                {/* Left Panel: Markdown Viewer */}
                <div
                  className={`flex-1 flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-zinc-900 text-zinc-100 ${
                    viewMode === 'markdown' ? 'w-full' : viewMode === 'split' ? 'w-1/2' : 'hidden'
                  } print:hidden`}
                >
                  <div className="px-3 py-1.5 bg-zinc-950 text-zinc-400 font-mono text-[11px] border-b border-zinc-800 flex justify-between items-center">
                    <span>{selectedDetail.filename}</span>
                    <span>{selectedDetail.word_count} palabras</span>
                  </div>
                  <textarea
                    readOnly
                    value={selectedDetail.markdown}
                    className="flex-1 w-full p-4 font-mono text-xs leading-relaxed bg-transparent text-zinc-200 resize-none focus:outline-hidden selection:bg-zinc-700"
                    spellCheck={false}
                  />
                </div>

                {/* Right Panel: Live Resume Preview (A4 Paper) */}
                <div
                  className={`flex-1 overflow-y-auto bg-zinc-200/80 dark:bg-zinc-950 ${
                    viewMode === 'preview'
                      ? 'w-full'
                      : viewMode === 'split'
                      ? 'w-1/2'
                      : 'hidden print:block'
                  } print:w-full print:bg-white print:overflow-visible print:p-0 print:m-0`}
                >
                  <LiveResumePreview markdown={selectedDetail.markdown} />
                </div>
              </div>
            ) : (
              /* ATS Audit Scorecard View */
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-zinc-50 dark:bg-zinc-950">
                <div className="max-w-4xl mx-auto space-y-4">
                  {isAuditing && (
                    <div className="p-12 text-center text-zinc-500 font-mono text-xs space-y-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xs">
                      <Loader2 className="w-7 h-7 animate-spin mx-auto text-emerald-500" />
                      <p className="font-semibold text-zinc-800 dark:text-zinc-200">
                        Auditando currículum con IA...
                      </p>
                      <p className="text-[11px] text-zinc-400">
                        Evaluando palabras clave ATS, impacto cuantificable Google XYZ y relevancia.
                      </p>
                    </div>
                  )}

                  {auditError && (
                    <div className="p-4 rounded bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 font-mono text-xs flex items-start space-x-2">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{auditError}</span>
                    </div>
                  )}

                  {!isAuditing && selectedDetail.evaluation && (
                    <div className="space-y-4">
                      <ScorecardView evaluation={selectedDetail.evaluation} />
                    </div>
                  )}

                  {!isAuditing && !selectedDetail.evaluation && (
                    <div className="p-10 text-center text-zinc-400 font-mono text-xs space-y-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xs">
                      <ShieldCheck className="w-10 h-10 mx-auto text-zinc-300 dark:text-zinc-600" />
                      <p className="font-semibold text-zinc-800 dark:text-zinc-200 text-sm font-sans">
                        Este currículum aún no cuenta con un informe ATS guardado
                      </p>
                      <p className="text-xs text-zinc-500 max-w-md mx-auto font-sans leading-relaxed">
                        Puedes evaluar la compatibilidad de palabras clave, relevancia del cargo y viñetas cuantificadas con IA ahora mismo.
                      </p>
                      <div className="pt-2">
                        <button
                          type="button"
                          onClick={handleRunAudit}
                          className="inline-flex items-center space-x-1.5 px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-sans font-medium transition-colors shadow-xs cursor-pointer"
                        >
                          <ShieldCheck className="w-4 h-4" />
                          <span>Auditar compatibilidad ATS ahora</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Hidden container for print support even when on ATS tab */}
                <div className="hidden print:block print:w-full print:bg-white print:overflow-visible print:p-0 print:m-0">
                  <LiveResumePreview markdown={selectedDetail.markdown} />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
