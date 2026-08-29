// "use client";

// import { useMemo, useState } from "react";
// import { contests, getFeaturedContest } from "@/lib/contests/mock-data";
// import { ContestHero } from "@/components/contests/ContestHero";
// import { ContestCard } from "@/components/contests/ContestCard";
// import { FilterTabs, FilterValue } from "@/components/contests/FilterTabs";

// export default function ContestsPage() {
//   const featured = useMemo(() => getFeaturedContest(), []);
//   const [filter, setFilter] = useState<FilterValue>("all");

//   const rest = contests.filter((c) => c.id !== featured.id);
//   const filtered = rest.filter((c) => filter === "all" || c.status === filter);

//   return (
//     <main className="min-h-screen bg-white">
//       <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
//         <ContestHero contest={featured} />

//         <div className="mt-12 flex items-center justify-between">
//           <h2 className="font-[var(--font-display)] text-xl text-[#121212]">
//             Boshqa musobaqalar
//           </h2>
//           <FilterTabs value={filter} onChange={setFilter} />
//         </div>

//         {filtered.length === 0 ? (
//           <p className="mt-8 rounded-xl border border-dashed border-[#E4E1D9] py-14 text-center text-sm text-[#8A8677]">
//             Bu holatda hozircha musobaqa yo'q.
//           </p>
//         ) : (
//           <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
//             {filtered.map((c, i) => (
//               <ContestCard key={c.id} contest={c} index={i} />
//             ))}
//           </div>
//         )}
//       </div>
//     </main>
//   );
// }


"use client";

export default function ContestsPage() {
  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto flex min-h-[70vh] max-w-7xl items-center justify-center px-5 py-10 sm:px-8">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-[#E4E1D9] bg-[#FAF9F5]">
            <span className="text-2xl">🏆</span>
          </div>

          <h1 className="font-[var(--font-display)] text-3xl text-[#121212]">
            Musobaqalar
          </h1>

          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-[#8A8677]">
            Musobaqalar bo‘limi hozircha ishlab chiqilmoqda.
            Tez orada bu yerda turli xil dasturlash musobaqalari
            va contestlar paydo bo‘ladi.
          </p>

          <div className="mt-8 inline-flex items-center rounded-full border border-[#E4E1D9] bg-[#FAF9F5] px-4 py-2 text-xs font-medium text-[#8A8677]">
            Tez orada 🚀
          </div>
        </div>
      </div>
    </main>
  );
}