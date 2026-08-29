import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";
import ApiProxy from "@/app/api/proxy";
import { Badge } from "@/components/ui/badge";
import { levelLabel, levelBadgeClass } from "@/lib/levels";
import { Zap, ShieldCheck } from "lucide-react";
import { Heatmap } from "./Heatmap";
import { ProblemsStatsCard } from "./ProblemsStatsCard";
import { ProfileTabs } from "./ProfileTabs";

export const dynamic = "force-dynamic"; // profil ma'lumotlari doim yangi bo'lishi kerak

interface UserProfileResponse {
  telegram_id: number;
  username: string;
  phone: string | null;
  full_name: string;
  last_login: string | null;
  is_owner: boolean;
  profile: { avatar: string | null; bio: string | null; website: string | null } | null;
  stats: { xp: number; level: string } | null;
}

interface RouteParams {
  params: Promise<{ username: string }>;
}

async function getProfile(username: string) {
  const res = await ApiProxy.get<UserProfileResponse>(`/user/${username}`, {
    withAuth: true,
    cache: "no-store",
  });
  if (res.status === 404) return null;
  return res.data;
}

// ============================================================
// SEO METADATA — har bir profil uchun dinamik
// ============================================================

export async function generateMetadata({ params }: RouteParams): Promise<Metadata> {
  const { username } = await params;
  const user = await getProfile(username);

  if (!user) {
    return { title: "Foydalanuvchi topilmadi" };
  }

  const displayName = user.full_name || user.username;
  const xp = user.stats?.xp ?? 0;
  const level = levelLabel(user.stats?.level ?? "beginner");

  const title = `${displayName} (@${user.username}) — CfM Contest profili`;
  const description = user.profile?.bio
    ? user.profile.bio.slice(0, 155)
    : `${displayName} CfM Contest platformasida ${xp} XP to'plagan (${level} darajasi). Yechilgan masalalar, sertifikatlar va kurslardagi progressni ko'ring.`;

  const canonical = `/user/${user.username}`;
  const ogImage = user.profile?.avatar || "/cfm_logo.webp";

  return {
    title,
    description,
    alternates: { canonical },
    robots: { index: true, follow: true },
    openGraph: {
      title,
      description,
      url: canonical,
      type: "profile",
      images: [{ url: ogImage, width: 400, height: 400, alt: `${displayName} profili` }],
    },
    twitter: {
      card: "summary",
      title,
      description,
      images: [ogImage],
    },
  };
}

// ============================================================
// SAHIFA
// ============================================================

export default async function UserProfilePage({ params }: RouteParams) {
  const { username } = await params;
  const user = await getProfile(username);

  if (!user) {
    notFound();
  }

  const displayName = user.full_name || user.username;
  const xp = user.stats?.xp ?? 0;
  const level = user.stats?.level ?? "beginner";

  // Google uchun structured data (schema.org ProfilePage)
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    dateModified: user.last_login ?? undefined,
    mainEntity: {
      "@type": "Person",
      name: displayName,
      alternateName: user.username,
      description: user.profile?.bio ?? undefined,
      image: user.profile?.avatar ?? undefined,
      url: `https://cfmcontest.uz/user/${user.username}`,
    },
  };

  return (
    <main className="min-h-screen bg-[#FAFAF7]">
      {/* SEO: structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ---------------- HERO: nafis qora blok ---------------- */}
      <section className="relative overflow-hidden bg-[#121212] px-4 py-16 text-white sm:py-20">
        {/* Signature: avatar orqasidagi juda xira, iliq gold nur — dramatik emas, faqat chuqurlik beradi */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/3 rounded-full opacity-[0.08] blur-3xl sm:left-28 sm:translate-x-0"
          style={{ background: "radial-gradient(circle, #D9AE55 0%, transparent 70%)" }}
        />

        <div className="relative mx-auto flex max-w-5xl flex-col items-center gap-6 text-center sm:flex-row sm:text-left">
          <div className="relative size-24 shrink-0 overflow-hidden rounded-full border border-[#D9AE55]/20 bg-[#1A1A18] ring-4 ring-white/[0.03] sm:size-28">
            {user.profile?.avatar ? (
              <Image
                src={user.profile.avatar}
                alt={`${displayName} avatari`}
                fill
                sizes="112px"
                className="object-cover"
              />
            ) : (
              <div className="flex size-full items-center justify-center text-3xl font-semibold text-white/30">
                {displayName.slice(0, 1).toUpperCase()}
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            {/* SEO: sahifada yagona <h1> */}
            <h1 className="truncate text-2xl font-semibold tracking-tight sm:text-3xl">
              {displayName}
            </h1>
            <p className="mt-1 text-white/40">@{user.username}</p>

            {user.profile?.bio && (
              <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/60 sm:mx-0">
                {user.profile.bio}
              </p>
            )}

            <div className="mt-5 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <Badge className={`border ${levelBadgeClass(level)} px-3 py-1 text-xs`}>
                {levelLabel(level)}
              </Badge>
              <Badge className="flex items-center gap-1 border border-[#D9AE55]/25 bg-[#D9AE55]/10 px-3 py-1 text-xs text-[#D9AE55]">
                <Zap className="size-3" /> {xp.toLocaleString("uz-UZ")} XP
              </Badge>
              {user.is_owner && (
                <Badge className="flex items-center gap-1 border border-white/15 bg-white/[0.04] px-3 py-1 text-xs text-white/70">
                  <ShieldCheck className="size-3" /> Bu — sizning profilingiz
                </Badge>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- ASOSIY KONTENT: nafis, iliq oq fon ---------------- */}
      <section className="mx-auto max-w-5xl px-4 py-10 sm:py-12">
        {/*
          "Mening holatim" widjeti /problems/stats/ dan keladi, u JORIY
          login qilgan foydalanuvchining statistikasini qaytaradi — boshqa
          birovning profilida noto'g'ri ma'lumot chiqmasligi uchun faqat
          profil egasiga ko'rsatiladi.
        */}
        {user.is_owner ? (
          <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
            <ProblemsStatsCard />
            <Heatmap telegramId={user.telegram_id} />
          </div>
        ) : (
          <div className="mb-8">
            <Heatmap telegramId={user.telegram_id} />
          </div>
        )}

        <ProfileTabs username={user.username} telegramId={user.telegram_id} />
      </section>
    </main>
  );
}