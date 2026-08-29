// app/test/[slug]/page.tsx
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import Image from "next/image";
import Link from "next/link";
import { fetcher } from "@/lib/utils";
import { apiPost } from "@/lib/tests/api";
import { VideoPlayer } from "@/components/VideoPlayer";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { RaschExplainer } from "@/components/RaschExplainer";
import type {
  TestDetail,
  TestSessionHistoryResponse,
  StartSessionResponse,
  ApiError,
} from "@/lib/tests/types";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  PlayCircle,
  History,
  Timer,
  Shuffle,
  Heart,
  ListChecks,
  Check,
  Wallet,
  ShoppingCart,
  Lock,
  Loader2,
  User,
  X,
  VideoIcon,
  Target,
  TrendingUp,
  CircleCheck,
  CircleX,
  MinusCircle,
  Info,
  HelpCircle,
  Award,
  BarChart3,
  BrainCircuit,
} from "lucide-react";

/* ================================================================
   HELPERS
   ================================================================ */
function isOpenNow(test: TestDetail) {
  const now = Date.now();
  if (test.start && now < new Date(test.start).getTime()) return false;
  if (test.end && now > new Date(test.end).getTime()) return false;
  return true;
}

function fmtPrice(price?: number) {
  if (!price || price === 0) return "Bepul";
  return Number(price).toLocaleString("uz-UZ") + " so'm";
}

function fmtDate(dateStr?: string | null) {
  if (!dateStr) return "N/A";
  try {
    return new Date(dateStr).toLocaleString("uz-UZ", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

function ctaText(test: TestDetail) {
  const status = test.user?.status;
  if (status === "in_progress") return "Davom ettirish";
  if (status === "completed") {
    if (test.max_att === 0 || (test.user && test.user.count < test.max_att))
      return "Qayta topshirish";
    return "Natijalarni ko'rish";
  }
  return "Boshlash";
}

function historyStatusText(status: string) {
  const map: Record<string, string> = {
    completed: "Yakunlangan",
    in_progress: "Jarayonda",
    expired: "Muddati o'tgan",
  };
  return map[status] || status;
}

function historyBadgeClass(status: string) {
  if (status === "completed")
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (status === "in_progress")
    return "bg-blue-50 text-blue-700 border-blue-200";
  return "bg-slate-100 text-slate-600 border-slate-200";
}

/**
 * Backenddan kelgan θ (logit, -4..+4) ni 0-100% ko'rinishga o'tkazamiz.
 * Bu faqat vizual tushunarlilik uchun. Asosiy hisob-kitob backendda.
 */
function thetaToPercent(theta: number) {
  const pct = ((theta + 4) / 8) * 100;
  return Math.max(0, Math.min(100, pct));
}

function progressBarColor(passed: boolean, progress: number) {
  if (passed) return "bg-emerald-500";
  if (progress >= 40) return "bg-amber-500";
  return "bg-red-400";
}

function ProgressBar({
  progress,
  passed,
  label,
}: {
  progress: number;
  passed: boolean;
  label?: string;
}) {
  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-[11px] text-slate-500">
        <span>{label}</span>
        <span className="font-semibold text-slate-700">{Math.round(progress)}%</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all ${progressBarColor(
            passed,
            progress
          )}`}
          style={{ width: `${Math.round(progress)}%` }}
        />
      </div>
    </div>
  );
}

/* ================================================================
   INFO TOOLTIP COMPONENT
   ================================================================ */
function InfoTip({ children }: { children: React.ReactNode }) {
  const [show, setShow] = useState(false);
  return (
    <span
      className="relative inline-block align-middle"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <HelpCircle className="ml-1 inline size-3.5 cursor-help text-slate-400 hover:text-slate-600" />
      {show && (
        <span className="absolute bottom-full left-1/2 z-20 mb-2 w-56 -translate-x-1/2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs leading-relaxed text-slate-600 shadow-lg">
          {children}
          <span className="absolute left-1/2 top-full -mt-1 size-2 -translate-x-1/2 rotate-45 border-b border-r border-slate-200 bg-white" />
        </span>
      )}
    </span>
  );
}

/* ================================================================
   MAIN PAGE
   ================================================================ */
export default function TestDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;

  const {
    data: test,
    error,
    isLoading,
    mutate,
  } = useSWR<TestDetail>(slug ? `/api/tests/${slug}` : null, fetcher, {
    revalidateOnFocus: false,
  });

  const { data: history } = useSWR<TestSessionHistoryResponse>(
    slug ? `/api/test-session/${slug}/sessions?limit=10&offset=0` : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const [starting, setStarting] = useState(false);
  const [accessCodeModalOpen, setAccessCodeModalOpen] = useState(false);
  const [accessCode, setAccessCode] = useState("");
  const [accessCodeError, setAccessCodeError] = useState<string | null>(null);
  const [showExplainer, setShowExplainer] = useState(false);

  async function startTest(code: string | null) {
    if (!slug || starting) return;
    setStarting(true);
    setAccessCodeError(null);

    try {
      const res = await apiPost<StartSessionResponse>(
        `/test-session/${slug}/start`,
        {
          access_code: code || null,
        }
      );

      setAccessCodeModalOpen(false);

      sessionStorage.setItem(
        "quiz_active_session",
        JSON.stringify({
          session_id: res.session_id,
          slug,
          title: res.test_title,
          questions: res.questions,
          duration_minutes: res.duration_minutes,
          expires_at: res.expires_at,
          lifelines: res.lifelines,
        })
      );

      router.push(`/tests/exam?session=${res.session_id}`);
    } catch (e) {
      const err = e as ApiError;
      const detail = err.detail;
      if (
        err.status === 401 &&
        typeof detail === "object" &&
        detail?.code === "access_code_required"
      ) {
        setAccessCodeModalOpen(true);
      } else if (err.status === 403) {
        setAccessCodeError("Kirish kodi noto'g'ri.");
        setAccessCodeModalOpen(true);
      } else {
        alert(err.message || "Testni boshlab bo'lmadi.");
      }
    } finally {
      setStarting(false);
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-white">
        <div className="mx-auto max-w-7xl px-4 py-8 lg:px-6">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              <Skeleton className="aspect-video w-full rounded-xl" />
              <Skeleton className="h-7 w-2/3" />
              <Skeleton className="h-4 w-1/3" />
            </div>
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        </div>
      </main>
    );
  }

  if (error || !test) {
    return (
      <main className="min-h-screen bg-white">
        <div className="mx-auto max-w-7xl px-4 py-20 text-center">
          <p className="text-lg font-bold text-slate-900">Test topilmadi</p>
          <p className="mt-2 text-sm text-slate-500">
            {(error as ApiError)?.status === 404
              ? "Bunday test mavjud emas yoki faol emas."
              : "Yuklashda xatolik yuz berdi."}
          </p>
          <Link
            href="/tests"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Ro&apos;yxatga qaytish
          </Link>
        </div>
      </main>
    );
  }

  const open = isOpenNow(test);
  const isPaidNotPurchased =
    test.buy === false && !!test.price && test.price > 0;
  const passThresholdPercent = Math.round(thetaToPercent(test.pass_threshold));

  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto max-w-7xl px-4 py-8 lg:px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* =========================================================
              LEFT COLUMN
              ========================================================= */}
          <div className="lg:col-span-2">
            <Link
              href="/tests"
              className="mb-6 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
            >
              <ArrowLeft className="size-4" /> Testlar ro&apos;yxati
            </Link>

            {/* Video */}
            {test.video?.hls ? (
              <div className="mb-6">
                <VideoPlayer
                  src={test.video.hls}
                  poster={test.video.img}
                  title={test.title}
                />
              </div>
            ) : test.video?.img ? (
              <div className="relative mb-6 aspect-video overflow-hidden rounded-xl bg-slate-100">
                <Image
                  src={test.video.img}
                  alt={test.title}
                  fill
                  className="object-cover"
                  unoptimized
                />
              </div>
            ) : null}

            <h1 className="mb-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              {test.title}
            </h1>

            {/* Badges */}
            <div className="mb-6 flex flex-wrap items-center gap-2">
              {test.buy === true && (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                  <Check className="size-3" /> Xarid qilingan
                </span>
              )}
              {isPaidNotPurchased && (
                <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700">
                  <Wallet className="size-3" /> Pullik
                </span>
              )}
              {(test.buy === null || test.buy === undefined) && (
                <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
                  Bepul
                </span>
              )}
              {test.user && test.user.count > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600">
                  <History className="size-3" /> {test.user.count} marta
                  urinilgan
                </span>
              )}
              {test.video && (
                <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                  <VideoIcon className="size-3" /> Video mavjud
                </span>
              )}
            </div>

            {test.des && (
              <div className="mb-6">
                <MarkdownRenderer content={test.des} />
              </div>
            )}

            {/* Facts */}
            <div className="mb-8 flex flex-wrap items-center gap-4 text-sm text-slate-600">
              <span className="flex items-center gap-1.5">
                <ListChecks className="size-4" strokeWidth={1.5} />
                <b className="text-slate-900">{test.qty}</b> savol
              </span>
              <span className="flex items-center gap-1.5">
                <Timer className="size-4" strokeWidth={1.5} />
                <b className="text-slate-900">{test.time}</b> daqiqa
              </span>
              <span className="flex items-center gap-1.5">
                <Heart className="size-4" strokeWidth={1.5} />
                <b className="text-slate-900">{test.lifelines || 0}</b> ta
                lifeline
              </span>
              <span className="flex items-center gap-1.5">
                <Target className="size-4" strokeWidth={1.5} />
                O&apos;tish chegarasi:{""}
                <b className="text-slate-900">{passThresholdPercent}%</b>
                <InfoTip>
                  Bu testdan o'tish uchun kerak bo'lgan{" "}
                  <strong>bilim darajasi</strong>. Har bir savolning qiyinligi
                  hisobga olinadi.
                </InfoTip>
              </span>
              {test.rand && (
                <span className="flex items-center gap-1.5">
                  <Shuffle className="size-4" strokeWidth={1.5} />
                  Savollar tasodifiy tanlanadi
                </span>
              )}
            </div>

            {/* CTA */}
            <div className="mb-10">
              {isPaidNotPurchased ? (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-5">
                  <div>
                    <div className="text-lg font-bold text-slate-900">
                      {fmtPrice(test.price)}
                    </div>
                    <div className="text-xs text-slate-500">
                      Testni topshirish uchun sotib oling
                    </div>
                  </div>
                  <button
                    onClick={() => alert("To'lov tizimi tez orada ulanadi.")}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
                  >
                    <ShoppingCart className="size-4" /> Sotib olish
                  </button>
                </div>
              ) : (
                <>
                  <button
                    disabled={!open || starting}
                    onClick={() => startTest(null)}
                    className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {starting ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <PlayCircle className="size-4" />
                    )}
                    {starting ? "Boshlanmoqda..." : ctaText(test)}
                  </button>
                  {!open && (
                    <p className="mt-2 text-xs text-slate-500">
                      Bu test hozircha yopiq (vaqt oynasidan tashqarida).
                    </p>
                  )}
                </>
              )}
            </div>

            {/* =========================================================
                HISTORY TABLE (YANGILANGAN — ikki metrika bilan)
                ========================================================= */}
            {!!history?.data.length && (
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-bold text-slate-900">
                    Mening urinishlarim
                  </h2>
                  <button
                    onClick={() => setShowExplainer(!showExplainer)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                  >
                    <BrainCircuit className="size-3.5" />
                    {showExplainer ? "Yashirish" : "Natijalar qanday hisoblanadi?"}
                  </button>
                </div>

                {showExplainer && (
                  <div className="mb-4">
                    <RaschExplainer threshold={passThresholdPercent} />
                  </div>
                )}

                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-slate-100 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-500">
                      <tr>
                        <th className="px-4 py-2.5">Sana</th>
                        <th className="px-4 py-2.5">Holati</th>
                        <th className="px-4 py-2.5">
                          <span className="flex items-center gap-1">
                            Bilim darajasi
                            <InfoTip>
                              Rasch modeli asosida hisoblangan haqiqiy bilim
                              darajangiz. -4 dan +4 gacha logit skalada
                              o'lchanadi va 0-100% ko'rinishda chiqariladi.
                            </InfoTip>
                          </span>
                        </th>
                        <th className="px-4 py-2.5">
                          <span className="flex items-center gap-1">
                            Oddiy foiz
                            <InfoTip>
                              To'g'ri javoblar soni / Umumiy savollar × 100.
                              Bu har doim ham haqiqiy bilimni aks ettirmaydi.
                            </InfoTip>
                          </span>
                        </th>
                        <th className="px-4 py-2.5">Javoblar</th>
                        <th className="px-4 py-2.5">XP</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {history.data.map((s) => (
                        <tr key={s.session_id}>
                          <td className="px-4 py-2.5 font-mono text-xs text-slate-500">
                            {s.started_at}
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${historyBadgeClass(
                                s.status
                              )}`}
                            >
                              {historyStatusText(s.status)}
                            </span>
                          </td>
                          <td className="px-4 py-2.5">
                            {s.status === "completed" ? (
                              <div className="flex items-center gap-2">
                                <span className="w-24">
                                  <ProgressBar
                                    progress={s.progress}
                                    passed={s.passed}
                                    label="Bilim"
                                  />
                                </span>
                                {s.passed ? (
                                  <CircleCheck className="size-3.5 text-emerald-500" />
                                ) : (
                                  <CircleX className="size-3.5 text-slate-300" />
                                )}
                              </div>
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5">
                            {s.status === "completed" ? (
                              <span className="font-mono text-xs font-semibold text-slate-600">
                                {Math.round(s.raw_percentage ?? 0)}%
                              </span>
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-2.5 text-xs text-slate-500">
                              <span className="flex items-center gap-1 text-emerald-600">
                                <CircleCheck className="size-3" /> {s.correct}
                              </span>
                              <span className="flex items-center gap-1 text-red-500">
                                <CircleX className="size-3" /> {s.wrong}
                              </span>
                              <span className="flex items-center gap-1 text-slate-400">
                                <MinusCircle className="size-3" />{" "}
                                {s.unanswered}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5 font-mono text-slate-700">
                            {s.xp || 0}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* =========================================================
              RIGHT SIDEBAR (YANGILANGAN)
              ========================================================= */}
          <div>
            <div className="sticky top-24 space-y-4">
              {/* ASOSIY NATIJA KARTASI */}
              <div className="rounded-xl border border-slate-200 p-5">
                <h3 className="mb-1 flex items-center gap-2 text-base font-bold text-slate-900">
                  <BarChart3 className="size-4" strokeWidth={1.5} /> Sizning
                  natijangiz
                </h3>

                {!test.user ? (
                  <div className="mt-3 space-y-2">
                    <p className="text-sm text-slate-500">
                      Siz hali bu testni boshlamagansiz. Testni topshirib,
                      natijangizni shu yerda kuzating.
                    </p>
                    <div className="rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
                      <strong className="text-slate-700">Eslatma:</strong> Bu
                      testda har bir savolning qiyinligi har xil. Shuning uchun
                      biz sizning natijangizni ikki xil usulda ko'rsatamiz:{" "}
                      <em>oddiy foiz</em> va <em>bilim darajasi</em> (Rasch).
                    </div>
                  </div>
                ) : (
                  <>
                    {/* KATTA BILIM DARAJASI */}
                    <div className="mt-4 mb-2 flex items-end justify-between">
                      <div>
                        <div className="flex items-baseline gap-1">
                          <span className="font-mono text-4xl font-bold text-slate-900">
                            {Math.round(test.user.progress)}
                          </span>
                          <span className="text-lg font-semibold text-slate-400">
                            %
                          </span>
                        </div>
                        <div className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
                          <BrainCircuit className="size-3" />
                          Bilim darajasi (Rasch)
                          <InfoTip>
                            Bu raqam sizning haqiqiy bilim darajangizni
                            ko'rsatadi. Har bir savolning qiyinligi hisobga
                            olingan. Oddiy foizdan aniqroq.
                          </InfoTip>
                        </div>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${
                          test.user.passed
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-amber-200 bg-amber-50 text-amber-700"
                        }`}
                      >
                        {test.user.passed ? (
                          <>
                            <Award className="size-3.5" /> O&apos;tdingiz
                          </>
                        ) : (
                          <>
                            <TrendingUp className="size-3.5" /> Hali
                            o&apos;tmadingiz
                          </>
                        )}
                      </span>
                    </div>

                    <ProgressBar
                      progress={test.user.progress}
                      passed={test.user.passed}
                    />

                    {/* O'TISH CHEGARASI MARKERI */}
                    <div className="relative mt-1 h-4">
                      <div
                        className="absolute top-0 -translate-x-1/2"
                        style={{ left: `${passThresholdPercent}%` }}
                      >
                        <div className="flex flex-col items-center">
                          <div className="size-1.5 rounded-full bg-slate-400" />
                          <span className="mt-0.5 whitespace-nowrap text-[10px] font-medium text-slate-500">
                            O&apos;tish: {passThresholdPercent}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* FARQ HAQIDA XABAR */}
                    {!test.user.passed && (
                      <div className="mt-4 space-y-2">
                        <p className="flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                          <Info className="mt-0.5 size-3.5 shrink-0" />
                          O&apos;tish uchun yana{" "}
                          <b className="font-mono">
                            {Math.max(
                              0,
                              passThresholdPercent -
                                Math.round(test.user.progress)
                            )}
                            %
                          </b>{" "}
                          bilim darajasi kerak.
                        </p>
                      </div>
                    )}

                    {/* IKKI METRIKANI TAQQOSLASH */}
                    <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1 text-slate-500">
                          <ListChecks className="size-3.5" />
                          Oddiy foiz:
                          <InfoTip>
                            To'g'ri javoblar / Umumiy savollar. Masalan, 10
                            tadan 6 tasiga javob bersangiz = 60%.
                          </InfoTip>
                        </span>
                        <span className="font-mono font-semibold text-slate-700">
                          {Math.round(test.user.raw_pct ?? 0)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1 text-slate-500">
                          <BrainCircuit className="size-3.5" />
                          Bilim darajasi:
                          <InfoTip>
                            Rasch modeli asosida hisoblangan. Qiyin savollarni
                            to'g'ri javob berganingizda ko'proq o'sadi.
                          </InfoTip>
                        </span>
                        <span
                          className={`font-mono font-semibold ${
                            test.user.passed
                              ? "text-emerald-600"
                              : "text-slate-700"
                          }`}
                        >
                          {Math.round(test.user.progress)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1 text-slate-500">
                          <Target className="size-3.5" />
                          O&apos;tish chegarasi:
                        </span>
                        <span className="font-mono font-semibold text-slate-700">
                          {passThresholdPercent}%
                        </span>
                      </div>
                    </div>

                    {/* STATISTIKA */}
                    <div className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-100 pt-4">
                      <div className="rounded-lg bg-slate-50 px-3 py-2 text-center">
                        <div className="font-mono text-lg font-bold text-slate-900">
                          {test.user.count}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          urinish
                        </div>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 text-center">
                        <div className="font-mono text-lg font-bold text-slate-900">
                          {test.user.xp}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          jami XP
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* RASCH HAQIDA QISQA MA'LUMOT */}
              {test.user && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
                  <h4 className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-blue-900">
                    <BrainCircuit className="size-4" />
                    Bilim darajasi nima?
                  </h4>
                  <p className="text-xs leading-relaxed text-blue-800">
                    Bu testda har bir savolning qiyinligi turlicha.{" "}
                    <strong>Oddiy foiz</strong> faqat nechta savolga javob
                    berganingizni ko'rsatadi.{" "}
                    <strong>Bilim darajasi (Rasch)</strong> esa qaysi savollarga
                    javob berganingizni hisobga oladi — oson savollarga javob
                    berib yuqori foiz olish mumkin, lekin bilim darajasi
                    oshmaydi.
                  </p>
                  <button
                    onClick={() => setShowExplainer(!showExplainer)}
                    className="mt-2 text-xs font-medium text-blue-700 hover:text-blue-800"
                  >
                    {showExplainer ? "Yopish" : "Batafsil tushuntirish →"}
                  </button>
                </div>
              )}

              {/* VAQTLAR */}
              {(test.start || test.end) && (
                <div className="rounded-xl border border-slate-200 p-5">
                  <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                    <Timer className="size-4" /> Vaqtlar
                  </h4>
                  <div className="space-y-1 text-xs text-slate-500">
                    {test.start && (
                      <div className="flex justify-between">
                        <span>Boshlanish:</span>
                        <span className="font-mono">{fmtDate(test.start)}</span>
                      </div>
                    )}
                    {test.end && (
                      <div className="flex justify-between">
                        <span>Tugash:</span>
                        <span className="font-mono">{fmtDate(test.end)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ACCESS CODE MODAL */}
      {accessCodeModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setAccessCodeModalOpen(false)}
        >
          <div
            className="w-full max-w-sm rounded-xl bg-white p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-1 flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <Lock className="size-4" /> Kirish kodi kerak
              </h3>
              <button onClick={() => setAccessCodeModalOpen(false)}>
                <X className="size-4 text-slate-400" />
              </button>
            </div>
            <p className="mb-4 text-sm text-slate-500">
              Bu test yopiq. Davom etish uchun kirish kodini kiriting.
            </p>
            <input
              autoFocus
              type="text"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && startTest(accessCode.trim())}
              placeholder="Kirish kodi"
              className="mb-2 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm focus:border-slate-400 focus:outline-none"
            />
            {accessCodeError && (
              <p className="mb-3 text-xs text-red-600">{accessCodeError}</p>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setAccessCodeModalOpen(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                Bekor qilish
              </button>
              <button
                onClick={() => startTest(accessCode.trim())}
                disabled={starting}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
              >
                Tasdiqlash
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}