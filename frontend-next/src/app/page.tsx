"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { TeamSection } from "@/components/TeamSection";
import { OpportunitiesSection } from "@/components/OpportunitiesSection";

// Swiper React komponentlari va modullari
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination, Autoplay, EffectFade } from "swiper/modules";

// Swiper stillarini import qilish
import "swiper/css";
import "swiper/css/pagination";
import "swiper/css/effect-fade";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";

// 1. Kurs toifalari uchun mock ma'lumotlar
const CATEGORIES = [
  "Backend",
  "Frontend",
  "Database",
  "Mobil dasturlash",
  "UX dizayn",
  "Grafik dizayn",
];

// 2. Karusel (Slayder) uchun ma'lumotlar
const HERO_SLIDES = [
  {
    id: 1,
    title: "Computer Networkingni",
    author: "Otabek Nurmuhammad bilan",
    actionText: "o'rganing",
    buttonText: "Ishtirok etish",
    buttonLink: "/courses/networking",
    imageSrc: "/express-networking.png",
    imageAlt: "Express Networking kursi",
    bgColor: "from-blue-600/20 to-purple-600/20",
    badge: "Mashhur kurs",
  },
  {
    id: 2,
    title: "Full Stack Dasturlashni",
    author: "Azim Po'lat bilan",
    actionText: "o'zlashtiring",
    buttonText: "Boshlash",
    buttonLink: "/courses/fullstack",
    imageSrc: "/fullstack.png",
    imageAlt: "Full Stack kursi",
    bgColor: "from-green-600/20 to-teal-600/20",
    badge: "Yangi",
  },
  {
    id: 3,
    title: "DevOps va Cloud",
    author: "Henry Tseng bilan",
    actionText: "o'rganing",
    buttonText: "Qo'shilish",
    buttonLink: "/courses/devops",
    imageSrc: "/devops.png",
    imageAlt: "DevOps kursi",
    bgColor: "from-orange-600/20 to-red-600/20",
    badge: "Premium",
  },
  {
    id: 4,
    title: "UX/UI Dizaynni",
    author: "Nodir Halilov bilan",
    actionText: "mukammallashtiring",
    buttonText: "Sinab ko'rish",
    buttonLink: "/courses/uxui",
    imageSrc: "/uxui.png",
    imageAlt: "UX/UI kursi",
    bgColor: "from-pink-600/20 to-rose-600/20",
    badge: "Mashhur",
  },
];

const STEPS_DATA = [
  {
    number: 1,
    title: "O'zingizga mos masterklassni tanlaysiz",
    imageSrc: "/steps/step-1.svg",
    imageAlt: "Masterklass tanlash bosqichi",
  },
  {
    number: 2,
    title: "Berilgan darslarni o'rganib, vazifalarni bajarasiz.",
    imageSrc: "/steps/step-2.svg",
    imageAlt: "Darslarni o'rganish va amaliyot bosqichi",
  },
  {
    number: 3,
    title: "Amaliy mashg'ulotlarda qatnashing, sertifikatga ega bo'ling.",
    imageSrc: "/steps/step-3.svg",
    imageAlt: "Sertifikat olish bosqichi",
  },
];

export default function HomePage() {
  return (
    <>
    <main className="flex-1 w-full bg-slate-50/50 dark:bg-neutral-950 min-h-screen">
      {/* Asosiy Container */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20">
        
        {/* HERO SECTION - SWIPER BILAN (Fade effekt bilan) */}
        <div className="relative">
          <Swiper
            modules={[Pagination, Autoplay, EffectFade]}
            spaceBetween={0}
            slidesPerView={1}
            loop={true}
            effect="fade"
            fadeEffect={{
              crossFade: true,
            }}
            speed={800}
            autoplay={{
              delay: 3000,
              disableOnInteraction: false,
              pauseOnMouseEnter: true,
            }}
            pagination={{
              clickable: true,
              dynamicBullets: true,
            }}
            className="hero-swiper"
          >
            {HERO_SLIDES.map((slide) => (
              <SwiperSlide key={slide.id}>
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center min-h-[450px] py-8">
                  
                  {/* Chap Tomon: Matnlar va Tugma */}
                  <div className="lg:col-span-6 flex flex-col justify-center">
                    {/* Badge */}
                    <span className="inline-block px-4 py-1.5 rounded-full bg-blue-600/10 text-blue-600 dark:bg-blue-600/20 dark:text-blue-400 text-xs font-semibold tracking-wider uppercase mb-6 w-fit">
                      {slide.badge}
                    </span>

                    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-neutral-900 dark:text-neutral-50 tracking-tight leading-[1.15]">
                      <span className="text-blue-600 block mb-2">{slide.title}</span>
                      <span className="block text-neutral-800 dark:text-neutral-200">{slide.author}</span>
                      <span className="block text-neutral-800 dark:text-neutral-200">{slide.actionText}</span>
                    </h1>

                    <div className="mt-10">
                      <Link
                        href={slide.buttonLink}
                        className="inline-flex items-center justify-center bg-[#0d1527] text-white px-8 py-4 rounded-xl font-semibold text-sm hover:bg-opacity-90 transition-all active:scale-[0.98] shadow-sm hover:shadow-lg"
                      >
                        {slide.buttonText}
                        <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </Link>
                    </div>
                  </div>

                  {/* O'ng Tomon: Rasm joylashgan Banner */}
                  <div className="lg:col-span-6 flex justify-center lg:justify-end w-full">
                    <div className={`relative w-full max-w-[540px] aspect-[1.25/1] bg-gradient-to-br ${slide.bgColor} bg-[#090b0f] rounded-[32px] overflow-hidden p-8 flex items-center shadow-xl border border-neutral-800/40 transition-all duration-500 hover:border-neutral-700/60`}>
                      
                      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-white via-transparent to-transparent pointer-events-none" />

                      <div className="relative w-full h-full flex items-center justify-between z-10">
                        <div className="flex flex-col justify-between h-full py-4 max-w-[50%]">
                          <div className="text-orange-500 font-black text-3xl tracking-tighter select-none">
                            CfM Contest
                          </div>
                          
                          <div className="text-3xl sm:text-4xl font-black text-white tracking-tight uppercase leading-none">
                            {slide.title.split(" ").slice(0, 2).join(" ")} <br />
                            <span className="text-neutral-400 font-light">
                              {slide.title.split(" ").slice(2).join(" ") || "Course"}
                            </span>
                          </div>
                        </div>

                        <div className="absolute right-0 bottom-0 top-0 w-[55%] h-full flex items-end">
                          <div className="relative w-full h-[95%]">
                            <Image
                              src={slide.imageSrc}
                              alt={slide.imageAlt}
                              fill
                              priority
                              sizes="(max-width: 768px) 100vw, 300px"
                              className="object-contain object-bottom select-none drop-shadow-2xl"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
        </div>

        {/* PASTKI QISM: TOIFALAR (BADGES) */}
        <div className="mt-20 flex flex-wrap gap-3 max-w-4xl">
          {CATEGORIES.map((category, idx) => (
            <button
              key={idx}
              className="px-5 py-2.5 rounded-full bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:border-neutral-400 dark:hover:border-neutral-600 hover:text-neutral-900 dark:hover:text-white transition-all shadow-sm hover:shadow-md"
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* QADAMLAR BO'LIMI */}
      <section className="mt-24 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-center text-neutral-900 dark:text-neutral-50 mb-12 tracking-tight">
          CfM Contest qanday ishlaydi?
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {STEPS_DATA.map((step) => (
            <div 
              key={step.number} 
              className="bg-white dark:bg-neutral-900 border border-neutral-100 dark:border-neutral-800 rounded-[24px] p-6 flex flex-col items-start shadow-[0_4px_20px_rgba(0,0,0,0.02)] dark:shadow-none hover:shadow-[0_4px_30px_rgba(0,0,0,0.05)] transition-all group"
            >
              <div className="flex items-start gap-3 w-full mb-6">
                <div className="flex shrink-0 size-6 items-center justify-center rounded-full bg-[#1b223c] text-white text-xs font-bold font-mono mt-0.5">
                  {step.number}
                </div>
                <h3 className="text-base font-bold text-neutral-800 dark:text-neutral-200 leading-snug">
                  {step.title}
                </h3>
              </div>

              <div className="relative w-full aspect-[1.1/1] mt-auto flex items-end justify-center overflow-hidden rounded-xl bg-slate-50/50 dark:bg-neutral-950/40 p-2">
                <div className="relative w-full h-[95%] transition-transform duration-300 group-hover:scale-[1.03]">
                  <Image
                    src={step.imageSrc}
                    alt={step.imageAlt}
                    fill
                    sizes="(max-width: 768px) 100vw, 350px"
                    className="object-contain object-bottom select-none"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* OPPORTUNITIES SECTION */}
      <OpportunitiesSection />

      {/* TEAM SECTION */}
      <TeamSection />

      {/* Swiper stillarini global sozlash */}
      <style jsx global>{`
        .hero-swiper {
          overflow: hidden;
        }

        .hero-swiper .swiper-slide {
          opacity: 0 !important;
          transition: opacity 0.8s ease !important;
        }

        .hero-swiper .swiper-slide-active {
          opacity: 1 !important;
        }

        .hero-swiper .swiper-pagination {
          position: relative;
          margin-top: 2rem;
          display: flex;
          justify-content: center;
          gap: 0.5rem;
          z-index: 10;
        }

        .hero-swiper .swiper-pagination-bullet {
          width: 40px;
          height: 4px;
          border-radius: 4px;
          background: #d1d5db;
          opacity: 1;
          transition: all 0.5s ease;
          cursor: pointer;
        }

        .hero-swiper .swiper-pagination-bullet-active {
          background: #0d1527;
          width: 60px;
        }

        .hero-swiper .swiper-pagination-bullet:hover {
          background: #9ca3af;
          transform: scaleY(1.5);
        }

        /* Slayd ichidagi elementlar animatsiyasi */
        .hero-swiper .swiper-slide .lg\\:col-span-6 {
          transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .hero-swiper .swiper-slide:not(.swiper-slide-active) .lg\\:col-span-6 {
          transform: translateY(20px);
        }

        .hero-swiper .swiper-slide-active .lg\\:col-span-6 {
          transform: translateY(0);
        }

        /* Rasm animatsiyasi */
        .hero-swiper .swiper-slide .relative.w-full.h-\\[95\\%\\] {
          transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .hero-swiper .swiper-slide:not(.swiper-slide-active) .relative.w-full.h-\\[95\\%\\] {
          transform: scale(0.9);
          opacity: 0.6;
        }

        .hero-swiper .swiper-slide-active .relative.w-full.h-\\[95\\%\\] {
          transform: scale(1);
          opacity: 1;
        }

        /* Badge animatsiyasi */
        .hero-swiper .swiper-slide .inline-block {
          transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1) 0.2s;
        }

        .hero-swiper .swiper-slide:not(.swiper-slide-active) .inline-block {
          opacity: 0;
          transform: translateY(-20px);
        }

        .hero-swiper .swiper-slide-active .inline-block {
          opacity: 1;
          transform: translateY(0);
        }

        /* Title animatsiyasi */
        .hero-swiper .swiper-slide h1 {
          transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.3s;
        }

        .hero-swiper .swiper-slide:not(.swiper-slide-active) h1 {
          opacity: 0;
          transform: translateX(-30px);
        }

        .hero-swiper .swiper-slide-active h1 {
          opacity: 1;
          transform: translateX(0);
        }

        /* Button animatsiyasi */
        .hero-swiper .swiper-slide .mt-10 {
          transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.5s;
        }

        .hero-swiper .swiper-slide:not(.swiper-slide-active) .mt-10 {
          opacity: 0;
          transform: translateY(20px);
        }

        .hero-swiper .swiper-slide-active .mt-10 {
          opacity: 1;
          transform: translateY(0);
        }
      `}</style>
    </main>

    <Footer />
    </>
  );
}