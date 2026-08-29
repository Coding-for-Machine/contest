"use client";

import Image from "next/image";
import { FaLinkedin } from "react-icons/fa";
// Swiper React komponentlarini yuklash
import { Swiper, SwiperSlide } from "swiper/react";
// Swiper stillarini yuklash
import "swiper/css";
import "swiper/css/pagination";
import "swiper/css/autoplay";
// Kerakli modullarni yuklash
import { Pagination, Autoplay } from "swiper/modules";

const TEAM_MEMBERS = [
  {
    id: 1,
    name: "Otabek Nurmuhammad",
    role: "Software Engineer @ Dropbox",
    image: "/team/otabek.webp",
    linkedin: "https://linkedin.com",
    companies: [
      { name: "Dropbox", logo: "/logos/dropbox.svg" },
      { name: "Mobal.io", logo: "/logos/mobal.svg" },
      { name: "U-EDU", logo: "/logos/uedu.svg" }
    ]
  },
  {
    id: 2,
    name: "Diyorbek Sadullaev",
    role: "Software Engineer at Pinterest",
    image: "/team/diyorbek.webp",
    linkedin: "https://linkedin.com",
    companies: [
      { name: "Pinterest", logo: "/logos/pinterest.svg" },
      { name: "SuperDispatch", logo: "/logos/superdispatch.svg" }
    ]
  },
  {
    id: 3,
    name: "Henry Tseng",
    role: "DevOps Engineer @ Swisscom",
    image: "/team/henry.webp",
    linkedin: "https://linkedin.com",
    companies: [
      { name: "Swisscom", logo: "/logos/swisscom.svg" },
      { name: "Proton", logo: "/logos/proton.svg" },
      { name: "Meta", logo: "/logos/meta.svg" }
    ]
  },
  {
    id: 4,
    name: "Nodir Halilov",
    role: "Sr. Product Designer @ Super Dispatch",
    image: "/team/nodir.webp",
    linkedin: "https://linkedin.com",
    companies: [
      { name: "SuperDispatch", logo: "/logos/superdispatch.svg" },
      { name: "ADPList", logo: "/logos/adplist.svg" }
    ]
  },
  {
    id: 5,
    name: "Azim Po'lat",
    role: "Software Engineer @ Google",
    image: "/team/azim.webp",
    linkedin: "https://linkedin.com",
    companies: [
      { name: "Google", logo: "/logos/google.svg" },
      { name: "Amazon", logo: "/logos/amazon.svg" },
      { name: "Meta", logo: "/logos/meta.svg" }
    ]
  }
];

export function TeamSection() {
  return (
    <section className="w-full max-w-7xl mx-auto px-4 py-16 text-center select-none overflow-hidden">
      
      {/* Sarlavha */}
      <h2 className="text-black text-3xl md:text-5xl font-bold tracking-tight mb-14">
        Bizning jamoa
      </h2>

      {/* Swiper Karusel */}
      <Swiper
        modules={[Pagination, Autoplay]}
        spaceBetween={24} // Kartochkalar orasidagi masofa
        slidesPerView={1} // Mobil qurilmada 1 ta kartochka
        loop={true} // Cheksiz aylanish
        autoplay={{
          delay: 3000, // Har 3 soniyada avtomatik suriladi
          disableOnInteraction: false, // Foydalanuvchi teginsa ham to'xtab qolmaydi
        }}
        pagination={{
          clickable: true, // Pastdagi nuqtalarni bosib o'tkazish imkoniyati
          dynamicBullets: true, // Nuqtalarni chiroyli animatsiyali qilish
        }}
        // Ekran o'lchamlariga qarab kartochkalar sonini moslashtirish (Responsive)
        breakpoints={{
          640: { slidesPerView: 2 },  // Planshetda 2 ta
          1024: { slidesPerView: 3 }, // Kichik ekranda 3 ta
          1280: { slidesPerView: 4 }, // Katta ekranda rasmda turgandek 4 ta
        }}
        className="pb-14 team-swiper" // Pastki nuqtalar (dots) uchun joy tashlandi
      >
        {TEAM_MEMBERS.map((member) => (
          <SwiperSlide key={member.id}>
            <div className="bg-white rounded-[32px] overflow-hidden shadow-sm border border-neutral-100/80 flex flex-col p-4 text-left h-full transition-all duration-300 hover:shadow-md">
              
              {/* Rasm qismi */}
              <div className="w-full aspect-[4/5] relative rounded-[24px] overflow-hidden bg-neutral-50 mb-4">
                <Image
                  src={member.image}
                  alt={member.name}
                  fill
                  className="object-cover"
                  sizes="(max-w-7xl) 25vw, 100vw"
                />
              </div>

              {/* Ism va LinkedIn */}
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-bold text-lg text-neutral-900 leading-tight">
                  {member.name}
                </h3>
                <a 
                  href={member.linkedin} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-[#0077B5] hover:scale-110 transition-transform pt-0.5 shrink-0"
                >
                  <FaLinkedin size={20} />
                </a>
              </div>

              {/* Kasbi */}
              <p className="text-xs font-medium text-neutral-500 mt-1.5 mb-5 flex-grow">
                {member.role}
              </p>

              {/* Kompaniyalar logotiplari */}
              <div className="flex flex-wrap items-center gap-3 pt-3.5 border-t border-neutral-100">
                {member.companies.map((company, idx) => (
                  <div key={idx} className="relative h-4 w-16 opacity-75 hover:opacity-100 transition-opacity">
                    <Image
                      src={company.logo}
                      alt={company.name}
                      fill
                      className="object-contain object-left"
                    />
                  </div>
                ))}
              </div>

            </div>
          </SwiperSlide>
        ))}
      </Swiper>

      {/* Nuqtalar rangini Tailwind orqali boshqarish uchun qo'shimcha kichik stillar */}
      <style jsx global>{`
        .team-swiper .swiper-pagination-bullet-active {
          background: #000000 !important;
          width: 20px !important;
          border-radius: 4px !important;
        }
      `}</style>

    </section>
  );
}
