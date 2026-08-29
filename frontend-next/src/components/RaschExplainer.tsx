// components/RaschExplainer.tsx
"use client";

import { useState } from "react";
import { BrainCircuit, ChevronDown, ChevronUp, Lightbulb } from "lucide-react";

interface Props {
  threshold: number;
}

export function RaschExplainer({ threshold }: Props) {
  const [open, setOpen] = useState(true);

  return (
    <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-white p-5">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-left"
      >
        <h4 className="flex items-center gap-2 text-sm font-bold text-blue-900">
          <BrainCircuit className="size-4" />
          Natijalar qanday hisoblanadi?
        </h4>
        {open ? (
          <ChevronUp className="size-4 text-blue-600" />
        ) : (
          <ChevronDown className="size-4 text-blue-600" />
        )}
      </button>

      {open && (
        <div className="mt-3 space-y-3 text-xs leading-relaxed text-blue-800">
          {/* Vizual taqqoslash */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {/* Oddiy foiz */}
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="mb-1.5 flex items-center gap-1.5 font-semibold text-slate-900">
                <span className="inline-flex size-6 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold">
                  1
                </span>
                Oddiy foiz
              </div>
              <p className="text-slate-600">
                To'g'ri javoblar sonini umumiy savollarga bo'lib, 100 ga
                ko'paytirish. Masalan, 10 tadan 6 tasiga javob bersangiz —{" "}
                <strong>60%</strong>.
              </p>
              <div className="mt-2 rounded bg-slate-50 p-2 text-[11px] text-slate-500">
                ❌ Kamchilik: Oson savollarga javob berib, qiyinlarini tashlab
                ketish mumkin. Natija haqiqiy bilimni ko'rsatmasligi mumkin.
              </div>
            </div>

            {/* Rasch */}
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3">
              <div className="mb-1.5 flex items-center gap-1.5 font-semibold text-emerald-900">
                <span className="inline-flex size-6 items-center justify-center rounded-full bg-emerald-100 text-[10px] font-bold">
                  2
                </span>
                Bilim darajasi (Rasch)
              </div>
              <p className="text-emerald-800">
                Har bir savolning <strong>qiyinligi</strong> hisobga olinadi.
                Qiyin savolga javob bersangiz — ko'proq ball. Oson savolga xato
                bersangiz — katta jarima.
              </p>
              <div className="mt-2 rounded bg-emerald-100/50 p-2 text-[11px] text-emerald-700">
                ✅ Afzalligi: Sizning haqiqiy bilim darajangizni aniqroq
                o'lchaydi. Testdan testga farq qilmaydi.
              </div>
            </div>
          </div>

          {/* Misol */}
          <div className="rounded-lg border border-amber-100 bg-amber-50/60 p-3">
            <div className="mb-1 flex items-center gap-1.5 font-semibold text-amber-900">
              <Lightbulb className="size-3.5" />
              Misol
            </div>
            <p className="text-amber-800">
              Faraz qiling, testda 5 ta oson va 5 ta qiyin savol bor. Siz 5 ta
              osoniga to'g'ri, 5 ta qiyiniga noto'g'ri javob berdingiz.{" "}
              <strong>Oddiy foiz = 50%</strong>. Lekin Rasch modeli bu
              holatda sizning bilim darajangizni{" "}
              <strong>50% dan past</strong> deb baholaydi, chunki qiyin
              savollarni bilmagansiz.
            </p>
          </div>

          {/* O'tish chegarasi */}
          <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-white p-3">
            <div className="shrink-0">
              <div className="inline-flex size-8 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                {threshold}%
              </div>
            </div>
            <p className="text-slate-600">
              <strong>O'tish chegarasi:</strong> Bu testdan o'tish uchun
              bilim darajangiz kamida <strong>{threshold}%</strong> bo'lishi
              kerak. Bu chegara ham Rasch modeli orqali belgilangan.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}