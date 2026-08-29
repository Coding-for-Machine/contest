"use client";

import { useId, useRef, useState, useEffect, type KeyboardEvent } from "react";
import Image from "next/image";
import Link from "next/link";

import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination, Autoplay, Keyboard, A11y } from "swiper/modules";

import "swiper/css";
import "swiper/css/pagination";

/* ============================================================
   TYPES
============================================================ */

type Mentor = {
  name: string;
  role: string;
  image: string;
  logos: string[];
};

type ImageItem = {
  image: string;
  alt: string;
};

type MentorsTab = {
  id: string;
  label: string;
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
  type: "mentors";
  contentData: Mentor[];
};

type DoubleImageTab = {
  id: string;
  label: string;
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
  type: "double-images";
  contentData: [ImageItem, ImageItem];
};

type SingleImageTab = {
  id: string;
  label: string;
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
  type: "single-image";
  contentData: [ImageItem];
};

type CertificateTab = {
  id: string;
  label: string;
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
  type: "certificate-view";
  contentData: ImageItem[];
};

type OpportunityTab = MentorsTab | DoubleImageTab | SingleImageTab | CertificateTab;

/* ============================================================
   DATA
============================================================ */

const TABS_DATA: OpportunityTab[] = [
  {
    id: "jonli-darslar",
    label: "Jonli darslar",
    title: "Malakali mentorlar bilan masterklasslar",
    description:
      "Mentorni tanlang, sessiya buyurtma bering va mentor bilan bog'lanib, yangi bilimlarni mustahkamlang. Qirikkida faqatgina uzoq yillik tajribaga ega va o'z sohasining professionallari mentorlik qiladi.",
    buttonText: "Jonli darslarni ko'rish",
    buttonHref: "/live-lessons",
    type: "mentors",
    contentData: [
      {
        name: "Azim Po'lat",
        role: "Software Engineer",
        image: "/team/azim.webp",
        logos: ["/logos/google.svg", "/logos/amazon.svg", "/logos/meta.svg"],
      },
      {
        name: "Otabek Nurmuhammad",
        role: "Software Engineer",
        image: "/team/otabek.webp",
        logos: ["/logos/dropbox.svg", "/logos/mobal.svg", "/logos/uedu.svg"],
      },
      {
        name: "Diyorbek Sadullaev",
        role: "Software Engineer",
        image: "/team/diyorbek.webp",
        logos: ["/logos/pinterest.svg", "/logos/superdispatch.svg"],
      },
      {
        name: "Henry Tseng",
        role: "DevOps Engineer",
        image: "/team/henry.webp",
        logos: ["/logos/swisscom.svg", "/logos/proton.svg", "/logos/meta.svg"],
      },
      {
        name: "Nodir Halilov",
        role: "Sr. Product Designer",
        image: "/team/nodir.webp",
        logos: ["/logos/superdispatch.svg", "/logos/adplist.svg"],
      },
    ],
  },
  {
    id: "masalalar",
    label: "Masalalar",
    title: "Muammo yechuvchi bo'ling",
   description:
  "Faqat darslarni o‘qish va testlar yechish bilan o‘zingizni cheklamang. CfM Contest’da siz nafaqat bilim, balki amaliy tajriba ham olasiz. Olimpiadalar, testlar, masalalar va boshqa ko‘plab imkoniyatlarda qatnashib, o‘z bilimlaringizni amalda sinab ko‘ring.\n\nMuammolarni yechish va olgan bilimlaringizni amaliyotda qo‘llash orqali tajribangizni oshiring. Bu esa kelajakdagi intervyulardan muvaffaqiyatli o‘tishingizga yordam beradi. Amaliyotga tayyormisiz?",
    buttonText: "Ishtirok etish",
    buttonHref: "/problems",
    type: "double-images",
    contentData: [
      { image: "/platform/shell-task.webp", alt: "Shell amaliy vazifalar oynasi" },
      { image: "/platform/code-editor-problems.webp", alt: "Kod muharriri oynasi" },
    ],
  },
  {
    id: "testlar",
    label: "Testlar",
    title: "Quiz'lar orqali bilimingizni sinab ko'ring",
    description:
      "O'zingizga yoqqan kursni tanlang, darslarni o'zlashtiring, va dars oxiridagi ajoyib va qiziqarli savollarga javob berish orqali bilimingizni yanada mustahkamlang.\n\nMultiple-choice, true/false, fill in the blanks va boshqa turdagi savollar orqali bilimingizni sinab ko'ring.",
    buttonText: "Sinab ko'rish",
    buttonHref: "/tests",
    type: "single-image",
    contentData: [{ image: "/platform/test.webp", alt: "Quiz topshirish interfeysi" }],
  },
  {
    id: "sertifikat",
    label: "Sertifikat",
    title: "Kurslarni tugating va sertifikatga ega bo'ling",
    description:
      "Bizning platformada faqatgina kvizlar, amaliy vazifalar va masalalarni bajargan talabalar sertifikatga ega bo'lishadi.\n\nBizning sertifikat faqat bir parcha qog'oz emas, bilim olganingiz kafolatidir.",
    buttonText: "Sinab ko'rish",
    buttonHref: "/certificates",
    type: "certificate-view",
    contentData: [
      { image: "/platform/certificate-sample.webp", alt: "CFM Rasmiy Sertifikati" },
      { image: "/platform/certificate-sample-2.webp", alt: "CFM Sertifikat namunasi" },
      { image: "/platform/certificate-sample-3.webp", alt: "CFM Sertifikat dizayni" },
    ],
  },
];

/* ============================================================
   COMPONENT
============================================================ */

export function OpportunitiesSection() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [problemHover, setProblemHover] = useState(false);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const doubleImagesRef = useRef<HTMLDivElement | null>(null);
  const baseId = useId();

  const currentContent = TABS_DATA[activeIndex] ?? TABS_DATA[0];

  // Scroll bilan rasmlarni almashtirish — Intersection Observer
  useEffect(() => {
    const el = doubleImagesRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setProblemHover(true);
        } else {
          setProblemHover(false);
        }
      },
      {
        threshold: 0.4, // 40% ko'rinsa trigger bo'ladi
        rootMargin: "0px",
      }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [activeIndex]); // activeIndex o'zgarganda yangi ref uchun qayta ulash

  // Roving-tabindex keyboard navigation
  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const lastIndex = TABS_DATA.length - 1;
    let nextIndex: number | null = null;

    if (event.key === "ArrowRight") nextIndex = index === lastIndex ? 0 : index + 1;
    else if (event.key === "ArrowLeft") nextIndex = index === 0 ? lastIndex : index - 1;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = lastIndex;

    if (nextIndex !== null) {
      event.preventDefault();
      setActiveIndex(nextIndex);
      tabRefs.current[nextIndex]?.focus();
    }
  };

  return (
    <section className="w-full max-w-7xl mx-auto px-4 py-16 overflow-hidden">
      <h2 className="text-center text-black text-3xl md:text-5xl font-bold tracking-tight mb-12">
        CfM Contest imkoniyatlari
      </h2>

      <div className="w-full bg-[#f9f9fb] border border-neutral-100 rounded-[32px] md:rounded-[40px] p-5 md:p-10 lg:p-12 shadow-sm">
        {/* TABS */}
        <div
          role="tablist"
          aria-label="CfM Contest imkoniyatlari"
          className="flex flex-wrap items-center justify-center bg-[#f0eaf8]/60 p-1.5 rounded-[22px] max-w-3xl mx-auto mb-12 gap-1"
        >
          {TABS_DATA.map((tab, index) => {
            const active = index === activeIndex;
            const tabId = `${baseId}-tab-${tab.id}`;
            const panelId = `${baseId}-panel-${tab.id}`;

            return (
              <button
                key={tab.id}
                ref={(el) => {
                  tabRefs.current[index] = el;
                }}
                id={tabId}
                type="button"
                role="tab"
                aria-selected={active}
                aria-controls={panelId}
                tabIndex={active ? 0 : -1}
                onClick={() => setActiveIndex(index)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
                className={`
                  flex-1 min-w-[110px]
                  py-3 px-4
                  rounded-[18px]
                  text-sm font-semibold
                  transition-all duration-300
                  outline-none
                  focus-visible:ring-2 focus-visible:ring-[#121620] focus-visible:ring-offset-2
                  ${
                    active
                      ? "bg-[#121620] text-white shadow-lg"
                      : "text-neutral-500 hover:text-neutral-900 hover:bg-white/60"
                  }
                `}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* CONTENT */}
        <div
          id={`${baseId}-panel-${currentContent.id}`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-${currentContent.id}`}
          className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center"
        >
          {/* LEFT — copy */}
          <div className="lg:col-span-5 flex flex-col items-center lg:items-start text-center lg:text-left order-2 lg:order-1">
            <h3 className="text-neutral-900 text-2xl md:text-4xl font-extrabold tracking-tight leading-tight mb-6">
              {currentContent.title}
            </h3>

            <p className="text-neutral-500 text-sm md:text-base leading-relaxed mb-8 max-w-xl whitespace-pre-line">
              {currentContent.description}
            </p>

            <Link
              href={currentContent.buttonHref}
              className="
                inline-flex items-center justify-center
                bg-[#121620] text-white font-semibold
                px-10 md:px-12 py-4
                rounded-2xl
                shadow-lg shadow-black/10
                outline-none
                hover:-translate-y-0.5 hover:shadow-xl
                focus-visible:ring-2 focus-visible:ring-[#121620] focus-visible:ring-offset-2
                active:scale-95
                transition-all duration-300
              "
            >
              {currentContent.buttonText}
            </Link>
          </div>

          {/* RIGHT — visuals */}
          <div className="lg:col-span-7 w-full order-1 lg:order-2 opportunities-swiper">
            {currentContent.type === "mentors" && (
              <Swiper
                modules={[Pagination, Autoplay, Keyboard, A11y]}
                spaceBetween={16}
                slidesPerView={2}
                loop
                autoplay={{ delay: 2800, disableOnInteraction: false, pauseOnMouseEnter: true }}
                keyboard={{ enabled: true }}
                pagination={{ clickable: true, dynamicBullets: true }}
                breakpoints={{ 768: { slidesPerView: 3 } }}
                className="w-full pb-12"
              >
                {currentContent.contentData.map((mentor) => (
                  <SwiperSlide key={mentor.name} className="h-auto">
                    <article className="bg-white rounded-[22px] p-2.5 border border-neutral-100 shadow-xl shadow-neutral-200/40 flex flex-col h-full transition-transform duration-300 hover:-translate-y-1">
                      <div className="relative aspect-[4/5] overflow-hidden rounded-[17px] bg-neutral-100">
                        <Image
                          src={mentor.image}
                          alt={mentor.name}
                          fill
                          sizes="(max-width: 768px) 45vw, 220px"
                          className="object-cover"
                        />
                      </div>

                      <div className="px-1 pt-3">
                        <h4 className="font-bold text-sm text-neutral-900 truncate">{mentor.name}</h4>
                        <p className="text-[11px] text-neutral-400 mt-1 mb-3">{mentor.role}</p>

                        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-neutral-100">
                          {mentor.logos.map((logo) => (
                            <div key={logo} className="relative h-4 w-10">
                              <Image src={logo} alt="" fill sizes="40px" className="object-contain object-left" />
                            </div>
                          ))}
                        </div>
                      </div>
                    </article>
                  </SwiperSlide>
                ))}
              </Swiper>
            )}

            {currentContent.type === "double-images" && (
              <div
                ref={doubleImagesRef}
                onMouseEnter={() => setProblemHover(true)}
                onMouseLeave={() => setProblemHover(false)}
                className="relative w-full h-[360px] sm:h-[430px] md:h-[470px] group cursor-pointer rounded-[24px]"
              >
                {/* RASM 1 — Top-right */}
                <span
                  className={`
                    absolute top-0 right-0 w-[76%] aspect-[1.4/1]
                    rounded-[20px] overflow-hidden border border-white/80 shadow-2xl
                    transition-all duration-700 ease-[cubic-bezier(.22,1,.36,1)]
                    ${
                      problemHover
                        ? "z-20 translate-x-[8%] translate-y-[-14%] rotate-[5deg] scale-[0.94]"
                        : "z-0 translate-x-0 translate-y-0 rotate-[3deg] scale-100"
                    }
                  `}
                >
                  <Image
                    src={currentContent.contentData[0].image}
                    alt={currentContent.contentData[0].alt}
                    fill
                    sizes="(max-width: 1024px) 80vw, 600px"
                  />
                </span>

                {/* RASM 2 — Bottom-left */}
                <span
                  className={`
                    absolute bottom-0 left-0 w-[76%] aspect-[1.4/1]
                    rounded-[20px] overflow-hidden border border-white shadow-2xl
                    transition-all duration-700 ease-[cubic-bezier(.22,1,.36,1)]
                    ${
                      problemHover
                        ? "z-0 translate-x-[-8%] translate-y-[14%] rotate-[-5deg] scale-[0.94]"
                        : "z-10 translate-x-0 translate-y-0 rotate-[-3deg] scale-100"
                    }
                  `}
                >
                  <Image
                    src={currentContent.contentData[1].image}
                    alt={currentContent.contentData[1].alt}
                    fill
                    sizes="(max-width: 1024px) 80vw, 600px"
                  />
                </span>

                {/* Almashtirish belgisi */}
                <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-30 w-12 h-12 rounded-full bg-white shadow-xl flex items-center justify-center text-neutral-900 text-xl font-bold transition-all duration-500 group-hover:scale-110">
                  ↔
                </span>
              </div>
            )}

            {currentContent.type === "single-image" && (
              <div className="relative w-full h-[260px] sm:h-[330px] rounded-[22px] overflow-hidden bg-white border border-neutral-100 shadow-2xl">
                <Image
                  src={currentContent.contentData[0].image}
                  alt={currentContent.contentData[0].alt}
                  fill
                  sizes="(max-width: 1024px) 90vw, 650px"
                  className="object-cover object-top"
                  priority
                />
              </div>
            )}

            {currentContent.type === "certificate-view" && (
              <Swiper
                modules={[Pagination, Autoplay, Keyboard, A11y]}
                spaceBetween={16}
                slidesPerView={2}
                loop
                autoplay={{ delay: 3200, disableOnInteraction: false, pauseOnMouseEnter: true }}
                keyboard={{ enabled: true }}
                pagination={{ clickable: true, dynamicBullets: true }}
                breakpoints={{ 768: { slidesPerView: 3 } }}
                className="w-full pb-12"
              >
                {currentContent.contentData.map((item) => (
                  <SwiperSlide key={item.image} className="h-auto">
                    <div className="relative aspect-[3/4] rounded-[20px] overflow-hidden border border-neutral-100 shadow-xl transition-all duration-300 hover:-translate-y-1">
                      <Image
                        src={item.image}
                        alt={item.alt}
                        fill
                        sizes="(max-width: 768px) 45vw, 220px"
                        className="object-cover"
                      />
                    </div>
                  </SwiperSlide>
                ))}
              </Swiper>
            )}
          </div>
        </div>
      </div>

      <style jsx global>{`
        .opportunities-swiper .swiper-pagination-bullet-active {
          background: #121620 !important;
          width: 16px !important;
          border-radius: 4px !important;
        }
        .opportunities-swiper .swiper-pagination-bullet {
          background: #d1d5db !important;
          opacity: 1 !important;
        }
        .opportunities-swiper .swiper-pagination {
          bottom: 0 !important;
        }
        @media (prefers-reduced-motion: reduce) {
          .opportunities-swiper * {
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
          }
        }
      `}</style>
    </section>
  );
}