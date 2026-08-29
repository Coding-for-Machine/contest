// src/components/courses/course-faq.tsx
"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

const faqs = [
  {
    q: "Kursni qancha vaqtda tugatish mumkin?",
    a: "Kursning umumiy davomiyligi 12 soat atrofida. O'rtacha 2-3 haftada tugatishingiz mumkin.",
  },
  {
    q: "Kursdan so'ng sertifikat beriladimi?",
    a: "Ha, kursni muvaffaqiyatli yakunlaganingizdan so'ng PDF formatida sertifikat olasiz.",
  },
  {
    q: "Kurs materiallariga qancha vaqt davomida ega bo'laman?",
    a: "Kursni sotib olganingizdan so'ng materiallarga umrbod dostupga ega bo'lasiz.",
  },
  {
    q: "Mobil qurilmada o'qishim mumkinmi?",
    a: "Albatta! Platformamiz to'liq responsive va mobil qurilmalarga moslashtirilgan.",
  },
];

export function CourseFaq() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  return (
    <section id="faq">
      <h2 className="text-2xl font-semibold tracking-tight text-neutral-900 mb-6">
        Tez-tez so'raladigan savollar
      </h2>
      <div className="flex flex-col gap-2">
        {faqs.map((faq, idx) => {
          const isOpen = openIdx === idx;
          return (
            <div
              key={idx}
              className="rounded-lg border border-neutral-200 bg-white overflow-hidden"
            >
              <button
                onClick={() => setOpenIdx(isOpen ? null : idx)}
                className="flex w-full items-center justify-between px-5 py-4 text-left hover:bg-neutral-50 transition"
              >
                <span className="text-sm font-medium text-neutral-900">{faq.q}</span>
                <ChevronDown
                  className={`size-4 text-neutral-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
                />
              </button>
              {isOpen && (
                <div className="px-5 pb-4 text-sm text-neutral-600 leading-relaxed border-t border-neutral-100">
                  {faq.a}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}