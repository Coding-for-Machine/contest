"use client";

import { useState } from "react";

const FAQ_DATA = [
  {
    category: "Umumiy",
    questions: [
      {
        question: "CFM Contest nima?",
        answer:
          "CFM Contest — bilim olish, o‘z bilimini sinash va amaliy ko‘nikmalarni rivojlantirish uchun yaratilgan ta’lim platformasi. Platformada kurslar, masalalar, sinovlar, olimpiadalar va bilimni rivojlantirishga yordam beradigan boshqa imkoniyatlar mavjud.",
      },
      {
        question: "CFM Contest kimlar uchun?",
        answer:
          "CFM Contest bilimini oshirishni, yangi ko‘nikmalarni egallashni va o‘z darajasini sinab ko‘rishni istagan barcha o‘quvchilar uchun mo‘ljallangan. Boshlang‘ich darajadan yuqori darajagacha bo‘lgan ishtirokchilar o‘ziga mos imkoniyatlardan foydalanishi mumkin.",
      },
      {
        question: "Platformada nimalar qilish mumkin?",
        answer:
          "Platformada kurslarni o‘rganish, amaliy masalalarni yechish, sinovlarda qatnashish, olimpiadalarda ishtirok etish, o‘z natijalarini kuzatish va bilimni amaliyot orqali mustahkamlash mumkin.",
      },
    ],
  },
  {
    category: "Kurslar",
    questions: [
      {
        question: "Kurslar qanday tashkil etilgan?",
        answer:
          "Kurslar mavzular va darslarga bo‘lingan. Har bir dars orqali yangi bilimni o‘zlashtirasiz, keyin esa o‘rganganlaringizni amaliy topshiriqlar va sinovlar yordamida mustahkamlaysiz.",
      },
      {
        question: "Kurslarni o‘z vaqtimga mos ravishda o‘qiy olamanmi?",
        answer:
          "Ha. Platformadagi mavjud kurslarni o‘z vaqtingiz va imkoniyatingizga mos ravishda o‘rganishingiz mumkin. Muhimi, darslarni izchil o‘zlashtirish va berilgan topshiriqlarni bajarishdir.",
      },
      {
        question: "Darslarni tugatganimni qanday bilaman?",
        answer:
          "Platforma o‘tilgan darslar va bajarilgan topshiriqlarni hisobga oladi. Shu orqali qaysi mavzularni tugatganingizni va qaysi mavzular hali oldinda ekanini kuzatishingiz mumkin.",
      },
    ],
  },
  {
    category: "Masalalar",
    questions: [
      {
        question: "Masalalar nima uchun kerak?",
        answer:
          "Masalalar o‘rgangan bilimlaringizni amaliyotda qo‘llash uchun kerak. Ularni yechish orqali mantiqiy fikrlash, muammoni tahlil qilish, to‘g‘ri yechim topish va mustaqil ishlash ko‘nikmalaringiz rivojlanadi.",
      },
      {
        question: "Masalalarni yechishda xato qilsam nima bo‘ladi?",
        answer:
          "Xato qilish o‘rganish jarayonining tabiiy qismi. Masalani qayta ko‘rib chiqish, xatoni aniqlash va to‘g‘ri yechimga kelish orqali mavzuni yanada yaxshi o‘zlashtirasiz.",
      },
      {
        question: "Masalalar qiyinlashib boradimi?",
        answer:
          "Ha. Masalalar turli darajadagi bilim va ko‘nikmalarni talab qilishi mumkin. Murakkabroq masalalarni yechish orqali o‘z darajangizni bosqichma-bosqich oshirib borasiz.",
      },
    ],
  },
  {
    category: "Sinovlar",
    questions: [
      {
        question: "Sinovlar nima uchun kerak?",
        answer:
          "Sinovlar o‘rgangan bilimlaringizni tekshirish va qaysi mavzularni yaxshi o‘zlashtirganingizni aniqlash uchun xizmat qiladi. Ular orqali bilimni faqat o‘qibgina qolmay, amalda tekshirib ko‘rasiz.",
      },
      {
        question: "Sinovlar qanday tekshiriladi?",
        answer:
          "Sinovlar tizim tomonidan avtomatik ravishda tekshiriladi. Javoblaringiz belgilangan mezonlar asosida baholanadi va yakunda natijangiz ko‘rsatiladi.",
      },
      {
        question: "Sinov natijamni ko‘ra olamanmi?",
        answer:
          "Ha. Sinovni yakunlaganingizdan so‘ng natijangizni ko‘rishingiz mumkin. Natija orqali o‘z darajangizni baholab, qaysi mavzularga ko‘proq e’tibor berish kerakligini aniqlaysiz.",
      },
      {
        question: "Sinovda qayta qatnashish mumkinmi?",
        answer:
          "Bu sinovning shartlariga bog‘liq. Ayrim sinovlarda qayta topshirish imkoniyati mavjud bo‘lishi mumkin, ayrimlarida esa natija faqat bir marta hisobga olinadi.",
      },
    ],
  },
  {
    category: "Olimpiadalar",
    questions: [
      {
        question: "Olimpiadalarda qatnashish mumkinmi?",
        answer:
          "Ha. CFM Contest platformasida tashkil etiladigan olimpiada va musobaqalarda qatnashib, o‘z bilim va ko‘nikmalaringizni sinab ko‘rishingiz mumkin.",
      },
      {
        question: "Olimpiadada natijalar qanday aniqlanadi?",
        answer:
          "Natijalar olimpiada shartlariga muvofiq ravishda aniqlanadi. Ishtirokchilarning topshiriqlarni bajarishi, to‘g‘ri javoblari va boshqa belgilangan mezonlar hisobga olinadi.",
      },
      {
        question: "Olimpiadada boshqa ishtirokchilar bilan raqobatlashish mumkinmi?",
        answer:
          "Ha. Olimpiadalar orqali o‘z bilim va tezligingizni boshqa ishtirokchilar bilan sinab ko‘rishingiz mumkin. Bu sizga o‘z darajangizni yanada aniqroq baholashga yordam beradi.",
      },
    ],
  },
  {
    category: "Natijalar",
    questions: [
      {
        question: "Natijalarimni kuzata olamanmi?",
        answer:
          "Ha. Platformadagi mavjud imkoniyatlar orqali kurslardagi, sinovlardagi, masalalardagi va boshqa faoliyatlardagi natijalaringizni kuzatib borishingiz mumkin.",
      },
      {
        question: "Natijam past bo‘lsa nima qilishim kerak?",
        answer:
          "Past natija bilimni yaxshilash kerak bo‘lgan joylarni ko‘rsatadi. Qiyin bo‘lgan mavzularni qayta o‘rganish, ko‘proq masala yechish va sinovlarni takrorlash orqali natijangizni yaxshilashingiz mumkin.",
      },
      {
        question: "Natijalarim vaqt o‘tishi bilan yaxshilanadimi?",
        answer:
          "Muntazam o‘qish, amaliyot qilish va xatolar ustida ishlash bilim va ko‘nikmalaringizni rivojlantiradi. Natijangiz ham shunga mos ravishda yaxshilanib borishi mumkin.",
      },
    ],
  },
  {
    category: "Sertifikat",
    questions: [
      {
        question: "Sertifikat olish mumkinmi?",
        answer:
          "Ha. Sertifikat olish imkoniyati mavjud bo‘lgan kurslarda belgilangan talablarni bajargan ishtirokchilar sertifikat olishlari mumkin.",
      },
      {
        question: "Sertifikat olish uchun nimalarni bajarish kerak?",
        answer:
          "Bu kurs talablariga bog‘liq. Odatda darslarni o‘zlashtirish, amaliy topshiriqlarni bajarish va belgilangan sinovlardan muvaffaqiyatli o‘tish talab qilinadi.",
      },
      {
        question: "Sertifikat nimani anglatadi?",
        answer:
          "Sertifikat kurs yoki dastur bo‘yicha belgilangan talablarni bajarganingizni tasdiqlovchi hujjatdir. U sizning ushbu yo‘nalishda ma’lum bilim va ko‘nikmalarni egallaganingizni ko‘rsatadi.",
      },
    ],
  },
  {
    category: "Platformadan foydalanish",
    questions: [
      {
        question: "CFM Contest’dan foydalanish uchun ro‘yxatdan o‘tish kerakmi?",
        answer:
          "Platformadagi ayrim imkoniyatlardan foydalanish uchun akkaunt orqali tizimga kirish talab qilinadi. Ro‘yxatdan o‘tganingizdan so‘ng mavjud imkoniyatlardan foydalanishingiz mumkin.",
      },
      {
        question: "Akkauntim bilan bog‘liq muammo bo‘lsa nima qilaman?",
        answer:
          "Avvalo akkaunt ma’lumotlaringizni tekshiring. Muammo davom etsa, platformaning yordam xizmatiga murojaat qilishingiz mumkin.",
      },
      {
        question: "Telefon orqali ham foydalanish mumkinmi?",
        answer:
          "Ha. Platforma zamonaviy qurilmalarda foydalanish uchun moslashtirilgan. Telefon, planshet yoki kompyuter orqali platformadan foydalanishingiz mumkin.",
      },
    ],
  },
];

const CATEGORIES = ["Barchasi", ...FAQ_DATA.map((item) => item.category)];

export default function Page() {
  const [activeCategory, setActiveCategory] = useState("Barchasi");
  const [openIndex, setOpenIndex] = useState<string | null>(null);

  const categories =
    activeCategory === "Barchasi"
      ? FAQ_DATA
      : FAQ_DATA.filter((item) => item.category === activeCategory);

  return (
    <main className="min-h-screen bg-white">
      {/* HERO */}
      <section className="relative overflow-hidden border-b border-neutral-100">
        <div className="absolute left-1/2 top-0 -z-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-violet-100/50 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-20 md:px-8 md:pb-24 md:pt-28">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-600 shadow-sm">
              CFM Contest
            </div>

            <h1 className="text-4xl font-black tracking-tight text-neutral-950 md:text-6xl">
              Ko‘p so‘raladigan
              <span className="block text-neutral-500">
                savollar
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-neutral-500 md:text-lg">
              CFM Contest platformasi, kurslar, masalalar, sinovlar,
              olimpiadalar, natijalar va boshqa imkoniyatlar haqida
              kerakli javoblarni toping.
            </p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-5xl px-5 py-14 md:px-8 md:py-20">
        {/* CATEGORY */}
        <div className="mb-12 flex gap-2 overflow-x-auto pb-2">
          {CATEGORIES.map((category) => {
            const active = activeCategory === category;

            return (
              <button
                key={category}
                type="button"
                onClick={() => {
                  setActiveCategory(category);
                  setOpenIndex(null);
                }}
                className={`whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-semibold transition-all ${
                  active
                    ? "bg-neutral-950 text-white shadow-lg"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200 hover:text-neutral-950"
                }`}
              >
                {category}
              </button>
            );
          })}
        </div>

        {/* QUESTIONS */}
        <div className="space-y-10">
          {categories.map((group) => (
            <div key={group.category}>
              <div className="mb-4 flex items-center gap-3">
                <h2 className="text-xl font-bold text-neutral-950">
                  {group.category}
                </h2>

                <div className="h-px flex-1 bg-neutral-200" />
              </div>

              <div className="space-y-3">
                {group.questions.map((item, index) => {
                  const id = `${group.category}-${index}`;
                  const isOpen = openIndex === id;

                  return (
                    <div
                      key={id}
                      className={`overflow-hidden rounded-2xl border transition-all duration-300 ${
                        isOpen
                          ? "border-neutral-300 bg-white shadow-lg"
                          : "border-neutral-200 bg-neutral-50/70 hover:border-neutral-300 hover:bg-white"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() =>
                          setOpenIndex(isOpen ? null : id)
                        }
                        aria-expanded={isOpen}
                        className="flex w-full items-center justify-between gap-6 px-5 py-5 text-left md:px-6"
                      >
                        <span className="text-base font-semibold text-neutral-900 md:text-lg">
                          {item.question}
                        </span>

                        <span
                          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-xl text-neutral-700 transition-transform duration-300 ${
                            isOpen ? "rotate-45" : ""
                          }`}
                        >
                          +
                        </span>
                      </button>

                      <div
                        className={`grid transition-all duration-300 ${
                          isOpen
                            ? "grid-rows-[1fr] opacity-100"
                            : "grid-rows-[0fr] opacity-0"
                        }`}
                      >
                        <div className="overflow-hidden">
                          <p className="border-t border-neutral-100 px-5 pb-6 pt-5 text-sm leading-7 text-neutral-500 md:px-6 md:text-base">
                            {item.answer}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* BOTTOM CTA */}
      <section className="mx-auto max-w-5xl px-5 pb-20 md:px-8 md:pb-28">
        <div className="overflow-hidden rounded-[28px] bg-neutral-950 px-6 py-12 text-center text-white md:px-12 md:py-16">
          <h2 className="text-2xl font-bold md:text-4xl">
            Savolingizga javob topilmadimi?
          </h2>

          <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-neutral-400 md:text-base">
            Kerakli ma’lumotni topa olmagan bo‘lsangiz, CFM Contest
            jamoasi bilan bog‘laning. Sizga yordam berishdan
            mamnunmiz.
          </p>

          <button
            type="button"
            className="mt-8 rounded-2xl bg-white px-7 py-3.5 text-sm font-bold text-neutral-950 transition-transform hover:-translate-y-0.5 active:scale-95"
          >
            Biz bilan bog‘lanish
          </button>
        </div>
      </section>
    </main>
  );
}