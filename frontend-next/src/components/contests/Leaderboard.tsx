import { RegistrationPreview } from "@/lib/contests/types";

const medal: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

export function Leaderboard({ rows }: { rows: RegistrationPreview[] }) {
  if (rows.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-[#E4E1D9] py-10 text-center text-sm text-[#8A8677]">
        Musobaqa boshlangach reyting shu yerda ko&apos;rinadi.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-[#E4E1D9]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#E4E1D9] bg-[#F5F4EF] text-left text-xs text-[#8A8677]">
            <th className="w-14 px-4 py-2.5 font-normal">O&apos;rin</th>
            <th className="px-4 py-2.5 font-normal">Ishtirokchi</th>
            <th className="px-4 py-2.5 text-right font-normal">Aniqlik</th>
            <th className="px-4 py-2.5 text-right font-normal">XP</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-[#EFEDE6] last:border-0">
              <td className="px-4 py-2.5 font-[var(--font-mono)] text-[#8A8677]">
                {r.rank ? medal[r.rank] ?? r.rank : "—"}
              </td>
              <td className="px-4 py-2.5 text-[#121212]">{r.display_name}</td>
              <td className="px-4 py-2.5 text-right text-[#8A8677]">
                {r.accuracy_percent}%
              </td>
              <td className="px-4 py-2.5 text-right font-medium text-[#121212]">
                {r.total_xp_earned}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}