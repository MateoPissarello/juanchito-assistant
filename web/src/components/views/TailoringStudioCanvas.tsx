import React, { useState, useRef } from 'react';
import {
  Sparkles,
  Link2,
  FileText,
  Play,
  Square,
  Copy,
  Check,
  Download,
  Printer,
  Columns,
  Eye,
  Edit3,
  AlertCircle,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../../services/api';
import type { StreamProgressEvent, TailoringReport } from '../../types/profile';
import { LiveResumePreview } from './LiveResumePreview';
import { ScorecardView } from './ScorecardView';

export const TailoringStudioCanvas: React.FC = () => {
  // Input State
  const [inputMode, setInputMode] = useState<'url' | 'text'>('url');
  const [jobUrl, setJobUrl] = useState('');
  const [jobText, setJobText] = useState('');
  const [maxIterations, setMaxIterations] = useState<number>(3);
  const [language, setLanguage] = useState<'en' | 'es'>('en');

  // Execution & Progress State
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [progressMessage, setProgressMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Output State
  const [markdown, setMarkdown] = useState<string>('');
  const [report, setReport] = useState<TailoringReport | null>(null);

  // UI View Mode (split, editor, preview)
  const [viewMode, setViewMode] = useState<'split' | 'editor' | 'preview'>('split');
  const [copied, setCopied] = useState(false);

  // Abort controller reference for cancelling SSE stream
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleStartOptimization = async () => {
    const jobInput = inputMode === 'url' ? jobUrl.trim() : jobText.trim();
    if (!jobInput) {
      setErrorMessage(
        inputMode === 'url'
          ? 'Por favor ingresa la URL de la vacante (ej. LinkedIn, Greenhouse o Lever)'
          : 'Por favor pega la descripción o requisitos de la vacante'
      );
      return;
    }

    setErrorMessage(null);
    setIsRunning(true);
    setCurrentStep(1);
    setProgressMessage('Iniciando optimización del currículum...');

    // Crear nuevo AbortController
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await api.streamTailor(
        jobInput,
        maxIterations,
        language,
        (event: StreamProgressEvent) => {
          if (event.type === 'analyzing') {
            setCurrentStep(1);
            setProgressMessage(event.message);
          } else if (event.type === 'matching') {
            setCurrentStep(2);
            setProgressMessage(event.message);
          } else if (event.type === 'writing') {
            setCurrentStep(3);
            setProgressMessage(event.message);
          } else if (event.type === 'evaluating') {
            setCurrentStep(4);
            setProgressMessage(event.message);
          } else if (event.type === 'completed' && event.report) {
            setCurrentStep(4);
            setProgressMessage('¡Optimización completada con éxito!');
            setReport(event.report);
            setMarkdown(event.report.final_markdown);
          } else if (event.type === 'error') {
            setErrorMessage(event.message);
          }
        },
        controller.signal
      );
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setErrorMessage(err.message || 'Error durante la optimización.');
      }
    } finally {
      setIsRunning(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsRunning(false);
    setProgressMessage('Optimización cancelada por el usuario.');
  };

  const handleCopyMarkdown = async () => {
    if (!markdown) return;
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Error copying to clipboard:', err);
    }
  };

  const handleDownloadMarkdown = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const company = report?.job.company_name?.replace(/[^\w-]/g, '_') || 'company';
    const title = report?.job.job_title?.replace(/[^\w-]/g, '_') || 'role';
    a.href = url;
    a.download = `resume_${company}_${title}_${language}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handlePrintPdf = () => {
    if (!markdown) return;
    const company = report?.job.company_name?.replace(/[^\w-]/g, '_') || 'company';
    const title = report?.job.job_title?.replace(/[^\w-]/g, '_') || 'role';
    const originalTitle = document.title;

    // Asignar el nombre del documento para que el diálogo del navegador prellene el nombre del archivo PDF
    document.title = `resume_${company}_${title}_${language}`;

    // Disparar la impresión nativa de alta fidelidad
    window.print();

    // Restaurar el título original después del evento
    setTimeout(() => {
      document.title = originalTitle;
    }, 1000);
  };

  // Conteo de palabras para presupuesto de 1 página
  const wordCount = markdown
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

  return (
    <div className="h-full flex flex-col overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Top Header & Input Bar */}
      <div className="p-4 sm:p-5 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shrink-0 print:hidden">
        <div className="max-w-7xl mx-auto space-y-4">
          {/* Header Title */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h1 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>Tailoring Studio</span>
              </h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                Adapta tu perfil profesional para maximizar el porcentaje de coincidencia ATS.
              </p>
            </div>

            {/* Controls: Iterations Selector + Language Selector + Input Mode */}
            <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
              {/* Iterations Selector */}
              <div className="flex items-center space-x-1 p-0.5 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/80">
                <span className="text-[10px] font-mono text-zinc-400 dark:text-zinc-500 px-1.5 uppercase select-none">
                  Rondas
                </span>
                {[1, 2, 3, 4, 5].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setMaxIterations(count)}
                    disabled={isRunning}
                    title={`Límite de hasta ${count} ${count === 1 ? 'ronda' : 'rondas'} de redacción y evaluación ATS`}
                    className={`px-2 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer ${
                      maxIterations === count
                        ? 'bg-white dark:bg-zinc-900 text-emerald-600 dark:text-emerald-400 font-bold shadow-xs'
                        : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
                    }`}
                  >
                    {count}x
                  </button>
                ))}
              </div>

              {/* Language Selector */}
              <div className="flex items-center space-x-1 p-0.5 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/80">
                <span className="text-[10px] font-mono text-zinc-400 dark:text-zinc-500 px-1.5 uppercase select-none">
                  Idioma
                </span>
                <button
                  type="button"
                  onClick={() => setLanguage('en')}
                  disabled={isRunning}
                  className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer ${
                    language === 'en'
                      ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
                  }`}
                >
                  EN
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage('es')}
                  disabled={isRunning}
                  className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer ${
                    language === 'es'
                      ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
                  }`}
                >
                  ES
                </button>
              </div>

              {/* Input Mode Selector */}
              <div className="flex items-center space-x-1 p-0.5 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/80">
                <button
                  type="button"
                  onClick={() => setInputMode('url')}
                  disabled={isRunning}
                  className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                    inputMode === 'url'
                      ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
                  }`}
                >
                  <Link2 className="w-3.5 h-3.5" />
                  <span>URL</span>
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode('text')}
                  disabled={isRunning}
                  className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                    inputMode === 'text'
                      ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Texto</span>
                </button>
              </div>
            </div>
          </div>

          {/* Input Controls */}
          <div className="flex flex-col sm:flex-row gap-2">
            {inputMode === 'url' ? (
              <div className="flex-1 relative">
                <input
                  type="url"
                  value={jobUrl}
                  onChange={(e) => setJobUrl(e.target.value)}
                  placeholder="https://boards.greenhouse.io/... o enlace de vacante en LinkedIn"
                  disabled={isRunning}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      handleStartOptimization();
                    }
                  }}
                  className="w-full text-xs font-mono px-3.5 py-2 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-zinc-100"
                />
              </div>
            ) : (
              <div className="flex-1">
                <textarea
                  value={jobText}
                  onChange={(e) => setJobText(e.target.value)}
                  placeholder="Pega aquí la descripción completa de la vacante, requisitos técnicos y responsabilidades..."
                  rows={2}
                  disabled={isRunning}
                  className="w-full text-xs font-mono p-3 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-zinc-100 resize-none"
                />
              </div>
            )}

            <div className="flex items-center space-x-2">
              {!isRunning ? (
                <button
                  type="button"
                  onClick={handleStartOptimization}
                  className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-4 py-2 rounded text-xs font-medium bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-zinc-200 dark:text-zinc-900 transition-colors shadow-xs cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Optimizar Currículum</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleCancel}
                  className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-4 py-2 rounded text-xs font-medium bg-rose-600 hover:bg-rose-700 text-white transition-colors cursor-pointer"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Cancelar</span>
                </button>
              )}
            </div>
          </div>

          {/* Stepper / Live Progress Banner */}
          {isRunning && (
            <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-500" />
                  <span className="font-medium text-zinc-900 dark:text-zinc-100 font-mono text-[11px]">
                    {progressMessage}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-zinc-400">Paso {currentStep} de 4</span>
              </div>

              {/* Step indicator pills */}
              <div className="grid grid-cols-4 gap-2 pt-1">
                {[
                  '1. Requisitos de Vacante',
                  '2. Experiencias & Proyectos',
                  '3. Redacción Google XYZ',
                  '4. Auditoría ATS',
                ].map((stepName, idx) => {
                  const stepNum = idx + 1;
                  const isDone = currentStep > stepNum;
                  const isCurrent = currentStep === stepNum;
                  return (
                    <div
                      key={stepName}
                      className={`px-2 py-1 rounded text-[10px] font-mono flex items-center space-x-1.5 transition-colors ${
                        isDone
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                          : isCurrent
                          ? 'bg-zinc-200 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-300 dark:border-zinc-700 font-semibold'
                          : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-400 border border-zinc-200 dark:border-zinc-800'
                      }`}
                    >
                      {isDone && <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />}
                      {isCurrent && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />}
                      <span className="truncate">{stepName}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3 rounded bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Scorecard View (si la evaluación está disponible) */}
          {report && !isRunning && <ScorecardView evaluation={report.final_evaluation} />}
        </div>
      </div>

      {/* Main Workspace: Split-View */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Workspace Toolbar */}
        <div className="px-4 py-2 bg-zinc-100 dark:bg-zinc-900/60 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between shrink-0 print:hidden">
          <div className="flex items-center space-x-2 text-xs">
            {/* View Mode Switches */}
            <div className="flex items-center space-x-1 p-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
              <button
                type="button"
                onClick={() => setViewMode('split')}
                title="Split View (Side-by-side)"
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'split'
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'hover:text-zinc-900 dark:hover:text-zinc-100'
                }`}
              >
                <Columns className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('editor')}
                title="Editor Markdown"
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'editor'
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'hover:text-zinc-900 dark:hover:text-zinc-100'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('preview')}
                title="Vista Previa de Impresión"
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'preview'
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'hover:text-zinc-900 dark:hover:text-zinc-100'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Word count pill */}
            {markdown && (
              <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400 px-2 py-0.5 rounded bg-zinc-200/60 dark:bg-zinc-800/60">
                {wordCount} palabras · {wordCount <= 420 ? 'Óptimo para 1 página' : 'Puede exceder 1 página'}
              </span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              disabled={!markdown}
              title="Copiar contenido Markdown al portapapeles"
              className="inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copiado' : 'Copiar Markdown'}</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadMarkdown}
              disabled={!markdown}
              title="Descargar archivo .md"
              className="inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Descargar .md</span>
            </button>

            <button
              type="button"
              onClick={handlePrintPdf}
              disabled={!markdown}
              title="Exportar currículum en PDF vectorial de 1 página"
              className="inline-flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-medium border border-emerald-600 dark:border-emerald-500 bg-emerald-600 dark:bg-emerald-500 text-white hover:bg-emerald-700 dark:hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors shadow-xs"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Descargar PDF</span>
            </button>
          </div>
        </div>

        {/* Content View Body */}
        <div className="flex-1 flex overflow-hidden print:overflow-visible print:block">
          {/* Left Panel: Markdown Editor */}
          <div
            className={`flex-1 flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-zinc-900 text-zinc-100 ${
              viewMode === 'editor' ? 'w-full' : viewMode === 'split' ? 'w-1/2' : 'hidden'
            } print:hidden`}
          >
            <div className="px-3 py-1.5 bg-zinc-950 text-zinc-400 font-mono text-[11px] border-b border-zinc-800 flex justify-between items-center">
              <span>markdown_source.md</span>
              <span>resume.lol syntax</span>
            </div>
            <textarea
              value={markdown}
              onChange={(e) => setMarkdown(e.target.value)}
              placeholder="El código Markdown generado se desplegará aquí y podrás editarlo directamente..."
              className="flex-1 w-full p-4 font-mono text-xs leading-relaxed bg-transparent text-zinc-200 resize-none focus:outline-hidden selection:bg-zinc-700"
              spellCheck={false}
            />
          </div>

          {/* Right Panel: Live Resume Preview */}
          <div
            className={`flex-1 overflow-y-auto bg-zinc-200/80 dark:bg-zinc-950 ${
              viewMode === 'preview' ? 'w-full' : viewMode === 'split' ? 'w-1/2' : 'hidden print:block'
            } print:w-full print:bg-white print:overflow-visible print:p-0 print:m-0`}
          >
            <LiveResumePreview markdown={markdown} />
          </div>
        </div>
      </div>
    </div>
  );
};
