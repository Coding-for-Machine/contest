import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProblem } from "@/lib/problems/api.server";
import { ProblemWorkspace } from "@/components/problems/problem-workspace";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const problem = await getProblem(slug);

  if (!problem) {
    return {
      title: "Masala topilmadi | CfM Contest",
      robots: { index: false },
    };
  }

  const title = `${problem.title} — Masala | CfM Contest`;
  const description = problem.desc
    ? problem.desc.replace(/\n+/g, " ").slice(0, 155)
    : `${problem.title} — ${problem.dif} darajali masala. Yechimni yuboring va ${problem.xp} XP to'plang.`;

  return {
    title,
    description,
    alternates: { canonical: `/problem/${problem.slug}` },
    robots: { index: true, follow: true },
    openGraph: {
      title,
      description,
      url: `/problem/${problem.slug}`,
      type: "article",
    },
  };
}

export default async function ProblemPage({ params }: Props) {
  const { slug } = await params;
  const problem = await getProblem(slug);

  if (!problem) {
    notFound();
  }

  return (
    <main className="min-h-screen">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "LearningResource",
            name: problem.title,
            description: problem.desc?.slice(0, 300),
            educationalLevel: problem.dif,
            about: problem.cate_name ?? undefined,
            url: `https://cfmcontest.uz/problem/${problem.slug}`,
          }),
        }}
      />
      <ProblemWorkspace problem={problem} />
    </main>
  );
}