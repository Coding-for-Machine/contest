"use client";

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
  type Ref,
} from "react";
import dynamic from "next/dynamic";
import type { ProblemDetail } from "@/lib/problems/types";
import { useAuth } from "@/context/AuthContext";
import { toBase64 } from "@/lib/problems/utils";
import { runCode, submitCode } from "@/lib/problems/api";
import submissionTracker from "@/lib/submissions/tracker";
import { TestPanel } from "./test-panel";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { cn } from "@/lib/utils";
import {
  Loader2,
  Lock,
  ChevronDown,
  Settings,
  RotateCcw,
  Copy,
  Check,
  Sun,
  Moon,
  Minus,
  Plus,
  Scan,
  Minimize,
  Info,
  X,
} from "lucide-react";
import type { RunResponse } from "@/lib/problems/types";
import type { editor as MonacoEditorTypes } from "monaco-editor";
import type { PanelImperativeHandle } from "react-resizable-panels";

const Editor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const MONACO_LANG_MAP: Record<string, string> = {
  python: "python",
  python3: "python",
  javascript: "javascript",
  typescript: "typescript",
  java: "java",
  cpp: "cpp",
  "c++": "cpp",
  c: "c",
  go: "go",
  rust: "rust",
  ruby: "ruby",
  php: "php",
  csharp: "csharp",
  "c#": "csharp",
  kotlin: "kotlin",
  swift: "swift",
  dart: "dart",
};

function getMonacoLang(name: string): string {
  return MONACO_LANG_MAP[name.toLowerCase()] || name.toLowerCase();
}

const FONT_SIZE_MIN = 11;
const FONT_SIZE_MAX = 24;

const paneToolbarButtonClass = cn(
  "flex h-7 w-7 items-center justify-center rounded-md text-neutral-400",
  "bg-transparent transition-colors",
  "hover:bg-neutral-100 hover:text-neutral-800"
);

export interface CodeEditorPanelHandle {
  run: () => void;
  submit: () => void;
  logConsole: (message: string) => void;
}

interface CodeEditorPanelProps {
  problem: ProblemDetail;
  onRunStateChange?: (isRunning: boolean) => void;
  onSubmitStateChange?: (isSubmitting: boolean) => void;
}

type VerticalLayout = "split" | "editor-full" | "console-full";

export const CodeEditorPanel = forwardRef(function CodeEditorPanel(
  { problem, onRunStateChange, onSubmitStateChange }: CodeEditorPanelProps,
  ref: Ref<CodeEditorPanelHandle>
) {
  const { isAuthenticated, loginRequiredRedirect } = useAuth();

  const [selectedLang, setSelectedLang] = useState(problem.langs[0]);
  const [codeMap, setCodeMap] = useState<Record<number, string>>(() => {
    const initial: Record<number, string> = {};
    problem.langs.forEach((lang) => {
      const starter = problem.func[lang.id];
      initial[lang.id] = starter?.code || "";
    });
    return initial;
  });

  const [activeBottomTab, setActiveBottomTab] = useState<"testcase" | "result">(
    "testcase"
  );
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runResults, setRunResults] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [fontSize, setFontSize] = useState(14);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [tabSize, setTabSize] = useState<2 | 4>(4);
  const [wordWrap, setWordWrap] = useState(true);
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [copied, setCopied] = useState(false);
  const [justSaved, setJustSaved] = useState(true);

  const [consoleNotice, setConsoleNotice] = useState<string | null>(null);
  const noticeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [vLayout, setVLayout] = useState<VerticalLayout>("split");
  const editorPaneRef = useRef<PanelImperativeHandle>(null);
  const consolePaneRef = useRef<PanelImperativeHandle>(null);

  const settingsRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<MonacoEditorTypes.IStandaloneCodeEditor | null>(null);

  const code = codeMap[selectedLang.id] || "";

  const setCode = useCallback((langId: number, value: string) => {
    setCodeMap((prev) => ({ ...prev, [langId]: value }));
    setJustSaved(false);
    const t = setTimeout(() => setJustSaved(true), 500);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    onRunStateChange?.(isRunning);
  }, [isRunning, onRunStateChange]);

  useEffect(() => {
    onSubmitStateChange?.(isSubmitting);
  }, [isSubmitting, onSubmitStateChange]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        settingsRef.current &&
        !settingsRef.current.contains(e.target as Node)
      ) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    return () => {
      if (noticeTimeoutRef.current) clearTimeout(noticeTimeoutRef.current);
    };
  }, []);

  const handleEditorMount = (
    editorInstance: MonacoEditorTypes.IStandaloneCodeEditor
  ) => {
    editorRef.current = editorInstance;
    editorInstance.onDidChangeCursorPosition((e) => {
      setCursorPos({ line: e.position.lineNumber, col: e.position.column });
    });
  };

  const handleCopyCode = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleResetCode = () => {
    const starter = problem.func[selectedLang.id];
    setCode(selectedLang.id, starter?.code || "");
  };

  const handleRun = useCallback(async () => {
    if (!isAuthenticated) {
      loginRequiredRedirect();
      return;
    }
    setIsRunning(true);
    setError(null);
    setRunResults(null);
    setActiveBottomTab("result");

    try {
      const res = await runCode({
        problem_id: problem.id,
        language_id: selectedLang.id,
        code: toBase64(code),
        stdin: "",
      });
      setRunResults(res);
    } catch (err: any) {
      setError(err.message || "Run jarayonida xatolik");
    } finally {
      setIsRunning(false);
    }
  }, [isAuthenticated, loginRequiredRedirect, problem.id, selectedLang, code]);

  const handleSubmit = useCallback(async () => {
    if (!isAuthenticated) {
      loginRequiredRedirect();
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setActiveBottomTab("result");

    try {
      const res = await submitCode({
        problem_id: problem.id,
        language_id: selectedLang.id,
        code: toBase64(code),
      });

      if (res.queued && res.task_id) {
        submissionTracker.start(res.task_id);
      }
    } catch (err: any) {
      setError(err.message || "Submit jarayonida xatolik");
    } finally {
      setIsSubmitting(false);
    }
  }, [isAuthenticated, loginRequiredRedirect, problem.id, selectedLang, code]);

  const logConsole = useCallback((message: string) => {
    if (noticeTimeoutRef.current) clearTimeout(noticeTimeoutRef.current);
    setConsoleNotice(message);
    noticeTimeoutRef.current = setTimeout(() => setConsoleNotice(null), 4000);
  }, []);

  useImperativeHandle(ref, () => ({
    run: handleRun,
    submit: handleSubmit,
    logConsole,
  }));

  const applyVLayout = (next: VerticalLayout) => {
    const editorPane = editorPaneRef.current;
    const consolePane = consolePaneRef.current;
    if (!editorPane || !consolePane) return;

    if (next === "editor-full") {
      consolePane.resize("0%");
      editorPane.resize("100%");
    } else if (next === "console-full") {
      editorPane.resize("0%");
      consolePane.resize("100%");
    } else {
      editorPane.resize("65%");
      consolePane.resize("35%");
    }
    setVLayout(next);
  };

  const toggleEditorMaximize = () =>
    applyVLayout(vLayout === "editor-full" ? "split" : "editor-full");
  const toggleConsoleMaximize = () =>
    applyVLayout(vLayout === "console-full" ? "split" : "console-full");

  if (!isAuthenticated) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 bg-white text-neutral-500">
        <Lock className="size-12 text-neutral-300" />
        <p className="text-sm">Kod yozish va yechim yuborish uchun tizimga kiring</p>
        <button
          onClick={() => loginRequiredRedirect()}
          className="rounded-lg bg-orange-600 px-5 py-2 text-sm font-medium text-white hover:bg-orange-700"
        >
          Kirish
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Toolbar */}
      <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-3 py-2">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 pl-1 text-sm font-medium text-neutral-700">
            <span className="text-neutral-400">&lt;/&gt;</span>
            Kod
          </div>

          <div className="h-4 w-px bg-neutral-200" />

          <div className="relative">
            <select
              value={selectedLang.id}
              onChange={(e) => {
                const lang = problem.langs.find(
                  (l) => l.id === Number(e.target.value)
                );
                if (lang) setSelectedLang(lang);
              }}
              className="appearance-none rounded-md border border-neutral-200 bg-white py-1 pl-3 pr-8 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 focus:border-orange-500 focus:outline-none"
            >
              {problem.langs.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} {l.version}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 size-3 -translate-y-1/2 text-neutral-400" />
          </div>
        </div>

        <div className="flex items-center gap-1 pr-14">
          <ToolbarIconButton label="Kodni nusxalash" onClick={handleCopyCode}>
            {copied ? (
              <Check className="size-3.5 text-emerald-500" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </ToolbarIconButton>

          <ToolbarIconButton
            label="Boshlang'ich kodga qaytarish"
            onClick={handleResetCode}
          >
            <RotateCcw className="size-3.5" />
          </ToolbarIconButton>

          <div className="relative" ref={settingsRef}>
            <ToolbarIconButton
              label="Muharrir sozlamalari"
              active={settingsOpen}
              onClick={() => setSettingsOpen((v) => !v)}
            >
              <Settings className="size-3.5" />
            </ToolbarIconButton>

            {settingsOpen && (
              <div className="absolute right-0 top-9 z-30 w-64 rounded-lg border border-neutral-200 bg-white p-3 shadow-lg">
                <SettingRow label="Shrift o'lchami">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        setFontSize((s) => Math.max(FONT_SIZE_MIN, s - 1))
                      }
                      className="flex size-6 items-center justify-center rounded-md border border-neutral-200 text-neutral-500 hover:bg-neutral-50"
                    >
                      <Minus className="size-3" />
                    </button>
                    <span className="w-6 text-center text-xs font-medium text-neutral-700 tabular-nums">
                      {fontSize}
                    </span>
                    <button
                      onClick={() =>
                        setFontSize((s) => Math.min(FONT_SIZE_MAX, s + 1))
                      }
                      className="flex size-6 items-center justify-center rounded-md border border-neutral-200 text-neutral-500 hover:bg-neutral-50"
                    >
                      <Plus className="size-3" />
                    </button>
                  </div>
                </SettingRow>

                <SettingRow label="Mavzu">
                  <div className="flex items-center gap-1 rounded-md border border-neutral-200 p-0.5">
                    <button
                      onClick={() => setIsDarkTheme(false)}
                      className={cn(
                        "flex size-6 items-center justify-center rounded",
                        !isDarkTheme
                          ? "bg-neutral-800 text-white"
                          : "text-neutral-400 hover:bg-neutral-50"
                      )}
                    >
                      <Sun className="size-3.5" />
                    </button>
                    <button
                      onClick={() => setIsDarkTheme(true)}
                      className={cn(
                        "flex size-6 items-center justify-center rounded",
                        isDarkTheme
                          ? "bg-neutral-800 text-white"
                          : "text-neutral-400 hover:bg-neutral-50"
                      )}
                    >
                      <Moon className="size-3.5" />
                    </button>
                  </div>
                </SettingRow>

                <SettingRow label="Tab kengligi">
                  <div className="flex items-center gap-1 rounded-md border border-neutral-200 p-0.5">
                    {[2, 4].map((size) => (
                      <button
                        key={size}
                        onClick={() => setTabSize(size as 2 | 4)}
                        className={cn(
                          "flex h-6 min-w-6 items-center justify-center rounded px-1.5 text-xs font-medium",
                          tabSize === size
                            ? "bg-neutral-800 text-white"
                            : "text-neutral-500 hover:bg-neutral-50"
                        )}
                      >
                        {size}
                      </button>
                    ))}
                  </div>
                </SettingRow>

                <SettingRow label="Qatorni o'rash" last>
                  <button
                    onClick={() => setWordWrap((v) => !v)}
                    className={cn(
                      "flex h-5 w-9 items-center rounded-full p-0.5 transition-colors",
                      wordWrap ? "bg-orange-500" : "bg-neutral-200"
                    )}
                    aria-pressed={wordWrap}
                    aria-label="Qatorni o'rash"
                  >
                    <span
                      className={cn(
                        "size-4 rounded-full bg-white shadow-sm transition-transform",
                        wordWrap && "translate-x-4"
                      )}
                    />
                  </button>
                </SettingRow>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Editor + Konsol */}
      <div className="min-h-0 flex-1">
        <ResizablePanelGroup orientation="vertical">
          <ResizablePanel
            panelRef={editorPaneRef}
            defaultSize="65%"
            minSize="0%"
            onResize={(size: any) => {
              if (size > 5 && vLayout === "editor-full") setVLayout("split");
            }}
          >
            <div className="group relative h-full">
              {vLayout !== "console-full" && (
                <div className="absolute right-2 top-2 z-20 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={toggleEditorMaximize}
                    aria-label={
                      vLayout === "editor-full"
                        ? "Muharrirni tiklash"
                        : "Muharrirni to'liq oynaga yoyish (100%)"
                    }
                    className={paneToolbarButtonClass}
                  >
                    {vLayout === "editor-full" ? (
                      <Minimize className="size-3.5" />
                    ) : (
                      <Scan className="size-3.5" />
                    )}
                  </button>
                </div>
              )}
              <Editor
                height="100%"
                language={getMonacoLang(selectedLang.name)}
                value={code}
                onChange={(v) => setCode(selectedLang.id, v || "")}
                onMount={handleEditorMount}
                theme={isDarkTheme ? "vs-dark" : "vs"}
                options={{
                  fontSize,
                  fontFamily: "JetBrains Mono, Fira Code, monospace",
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize,
                  insertSpaces: true,
                  wordWrap: wordWrap ? "on" : "off",
                  padding: { top: 16 },
                  lineNumbers: "on",
                  renderWhitespace: "selection",
                  bracketPairColorization: { enabled: true },
                  smoothScrolling: true,
                  cursorBlinking: "smooth",
                }}
                loading={
                  <div className="flex h-full items-center justify-center text-neutral-400">
                    <Loader2 className="size-5 animate-spin" />
                  </div>
                }
              />
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel
            panelRef={consolePaneRef}
            defaultSize="35%"
            minSize="0%"
            onResize={(size: any) => {
              if (size > 5 && vLayout === "console-full") setVLayout("split");
            }}
          >
            <div className="group relative flex h-full flex-col bg-neutral-50">
              {vLayout !== "editor-full" && (
                <div className="absolute right-2 top-1.5 z-20 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={toggleConsoleMaximize}
                    aria-label={
                      vLayout === "console-full"
                        ? "Konsolni tiklash"
                        : "Konsolni to'liq oynaga yoyish (100%)"
                    }
                    className={paneToolbarButtonClass}
                  >
                    {vLayout === "console-full" ? (
                      <Minimize className="size-3.5" />
                    ) : (
                      <Scan className="size-3.5" />
                    )}
                  </button>
                </div>
              )}

              {/* Status bar */}
              <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 bg-white px-4 py-1 text-[11px] text-neutral-400">
                <span className="flex items-center gap-1">
                  <span
                    className={cn(
                      "size-1.5 rounded-full transition-colors",
                      justSaved ? "bg-emerald-400" : "bg-amber-400"
                    )}
                  />
                  {justSaved ? "Saqlandi" : "Saqlanmoqda…"}
                </span>
                <span className="tabular-nums">
                  {cursorPos.line}-qator, {cursorPos.col}-ustun
                </span>
              </div>

              {consoleNotice && (
                <div className="flex shrink-0 items-center justify-between gap-2 border-b border-blue-100 bg-blue-50 px-4 py-1.5 text-xs text-blue-700">
                  <span className="flex items-center gap-1.5">
                    <Info className="size-3.5 shrink-0" />
                    {consoleNotice}
                  </span>
                  <button
                    onClick={() => setConsoleNotice(null)}
                    className="shrink-0 text-blue-400 transition-colors hover:text-blue-700"
                    aria-label="Xabarni yopish"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              )}

              <div className="min-h-0 flex-1">
                <TestPanel
                  activeTab={activeBottomTab}
                  onTabChange={setActiveBottomTab}
                  runResults={runResults}
                  isRunning={isRunning}
                  isSubmitting={isSubmitting}
                  error={error}
                  exam={problem.exam}
                />
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
});

function ToolbarIconButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className={cn(
        "flex h-7 w-7 items-center justify-center rounded-md text-neutral-500 transition-colors",
        "hover:bg-neutral-100 hover:text-neutral-800",
        active && "bg-neutral-100 text-neutral-800"
      )}
    >
      {children}
    </button>
  );
}

function SettingRow({
  label,
  children,
  last,
}: {
  label: string;
  children: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between py-1.5",
        !last && "border-b border-neutral-100"
      )}
    >
      <span className="text-xs text-neutral-600">{label}</span>
      {children}
    </div>
  );
}