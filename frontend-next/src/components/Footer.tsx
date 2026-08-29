"use client";

import Link from "next/link";
import Image from "next/image";
import { 
  FaLinkedinIn, 
  FaInstagram, 
  FaYoutube, 
  FaTelegramPlane, 
  FaGithub 
} from "react-icons/fa";

const FOOTER_LINKS = [
  { name: "Kurslar", href: "/courses" },
  { name: "Musobaqalar", href: "/contests" },
  { name: "Masalalar", href: "/problems" },
  { name: "CfM Contest Podcast", href: "https://www.youtube.com/@CodingforMachines" },
  { name: "FAQ", href: "/faq" },
];

const SOCIAL_LINKS = [
  { icon: FaLinkedinIn, href: "https://linkedin.com", label: "Linkedin" },
  { icon: FaInstagram, href: "https://instagram.com", label: "Instagram" },
  { icon: FaYoutube, href: "https://www.youtube.com/@CodingforMachines", label: "Youtube" },
  { icon: FaTelegramPlane, href: "https://t.me", label: "Telegram" },
  { icon: FaGithub, href: "https://github.com", label: "Github" },
];

export function Footer() {
  return (
    // bg-transparent orqali asosiy oq fon saqlanadi
    <div className="w-full flex flex-col items-center bg-transparent mt-20">
      
      {/* Tepadagi Qora Banner - Kengligi cheklangan va o'rtada (max-w-5xl) */}
      <div className="w-full max-w-5xl bg-[#121214] border border-neutral-800/60 rounded-[40px] p-8 md:p-14 text-center mb-16 relative flex flex-col items-center justify-center min-h-[300px] shadow-2xl mx-4">
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-white size-16 rounded-full flex items-center justify-center shadow-lg p-1.5 border border-neutral-800/10">
          <Image 
            src="/cfm_logo.webp" 
            alt="CfM Mini Logo" 
            width={56} 
            height={56} 
            className="rounded-full object-contain"
            priority 
          />
        </div>
        
        <h2 className="text-white text-2xl md:text-4xl font-bold tracking-tight max-w-2xl mt-4 leading-snug">
          O&apos;z kelajagingizni qurishni hoziroq boshlang!
        </h2>
        
        <Link 
          href="/user" 
          className="mt-8 bg-white text-black font-semibold px-10 py-3.5 rounded-xl hover:bg-neutral-200 transition-all duration-200 shadow-md active:scale-95 select-none"
        >
          Ishtirok etish
        </Link>
      </div>

      {/* FUTER QISMI: max-h-[380px] va overflow-hidden orqali pastga qarab cho'zilishi qat'iy cheklandi */}
      <footer className="w-full max-h-[380px] overflow-hidden bg-[#050508] text-neutral-400 font-sans pt-12 pb-8 px-6 rounded-t-[40px] border-t border-neutral-900/50 shadow-2xl">
        {/* Ichidagi kontent esa max-w-5xl orqali o'rtada ixcham turadi */}
        <div className="max-w-5xl mx-auto flex flex-col items-center">
          
          <div className="w-full flex flex-col md:flex-row items-center justify-between border-b border-neutral-900/60 pb-8 gap-8">
            <Link 
              href="/" 
              className="flex shrink-0 size-14 items-center justify-center rounded-full bg-black border border-neutral-800/30 p-1.5 select-none shadow-sm transition-transform hover:scale-105"
            >
              <Image 
                src="/cfm_logo.webp" 
                alt="CfM Logo" 
                width={44} 
                height={44} 
                className="rounded-full object-contain"
              />
            </Link>

            <nav className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
              {FOOTER_LINKS.map((link) => (
                <Link
                  key={link.name}
                  href={link.href}
                  className="text-sm font-medium text-neutral-300 hover:text-white transition-colors duration-150"
                >
                  {link.name}
                </Link>
              ))}
            </nav>

            <div className="hidden md:block w-14" />
          </div>

          <div className="flex items-center justify-center gap-8 mt-8">
            {SOCIAL_LINKS.map((social, index) => {
              const Icon = social.icon;
              return (
                <a
                  key={index}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={social.label}
                  className="text-neutral-500 hover:text-white transition-all duration-300 hover:scale-110 hover:-translate-y-1"
                >
                  <Icon size={22} />
                </a>
              );
            })}
          </div>

          <div className="flex items-center justify-center gap-6 mt-8 text-xs font-medium text-neutral-500">
            <Link href="/privacy" className="hover:text-neutral-300 transition-colors duration-150">
              Privacy Policy
            </Link>
            <Link href="/terms" className="hover:text-neutral-300 transition-colors duration-150">
              Terms of Service
            </Link>
          </div>

          <div className="mt-5 text-center font-mono text-[10px] text-neutral-600 tracking-widest uppercase">
            © {new Date().getFullYear()} CfM Contest LLC. Barcha huquqlar himoyalangan.
          </div>

        </div>
      </footer>
    </div>
  );
}
