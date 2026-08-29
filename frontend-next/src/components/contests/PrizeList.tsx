import { ContestPrize } from "@/lib/types";

const rankStyle: Record<number, { bg: string; text: string; ring: string }> = {
  1: { bg: "bg-[#FBF2DC]", text: "text-[#8A6413]", ring: "border-[#EFE0AF]" },
  2: { bg: "bg-[#F2F1EC]", text: "text-[#6B6A62]", ring: "border-[#DEDCD3]" },
  3: { bg: "bg-[#F7E9DE]", text: "text-[#8A5327]", ring: "border-[#EAD1BC]" },
};

export function PrizeList({ prizes }: { prizes: ContestPrize[] }) {
  const sorted = [...prizes].sort((a, b) => a.rank_target - b.rank_target);

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {sorted.map((p) => {
        const style = rankStyle[p.rank_target] ?? {
          bg: "bg-[#F5F4EF]",
          text: "text-[#8A8677]",
          ring: "border-[#E4E1D9]",
        };
        return (
          <div
            key={p.id}
            className={`rounded-xl border ${style.ring} ${style.bg} p-4`}
          >
            <span className={`font-[var(--font-mono)] text-xs font-medium ${style.text}`}>
              {p.rank_target}-o&apos;rin
            </span>
            <p className="mt-1.5 text-[15px] font-medium text-[#121212]">{p.title}</p>
            {p.description && (
              <p className="mt-0.5 text-xs text-[#8A8677]">{p.description}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}