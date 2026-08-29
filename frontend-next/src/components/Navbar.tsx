// Navbar.tsx
"use client";
import Image from "next/image";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Menu,
  X,
  LogOut,
  User,
  Phone,
  MessageCircle,
  ChevronDown,
  Code2,
  Trophy,
  BookOpen,
  FlaskConical,
  GraduationCap,
  Zap,
  Settings,
  Crown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NotificationBell } from "./NotificationBell";

const navLinks = [
  { href: "/problems", label: "Masalalar", icon: Code2 },
  { href: "/contests", label: "Musobaqalar", icon: Trophy },
  { href: "/courses", label: "Kurslar", icon: GraduationCap },
  { href: "/tests", label: "Testlar", icon: FlaskConical },
];

export function Navbar() {
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const pathname = usePathname();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setUserOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    setUserOpen(false);
  }, [pathname]);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 lg:px-8">
        {/* Logo */}
       <Link href="/" className="flex items-center gap-2.5">
        <Image
          src="/cfm_logo.webp"
          alt="CFM"
          width={32}
          height={32}
          className="size-8 rounded-md object-contain"
          priority
        />
        <span className="text-base font-semibold tracking-tight text-slate-900">
          CFM Contest
        </span>
      </Link>

        {/* Desktop Navigation */}
        <nav className="hidden items-center gap-0.5 md:flex">
          {navLinks.map((link) => {
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-4 rounded-md mx-3 px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-slate-100 text-slate-900"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <link.icon className="size-4" strokeWidth={1.5} />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Section */}
        <div className="flex items-center gap-1">
          {isLoading ? (
            <div className="h-8 w-24 animate-pulse rounded-md bg-slate-100" />
          ) : isAuthenticated && user ? (
            <div className="flex items-center gap-2">
              {/* Notification Bell */}
              <NotificationBell />

              {/* User Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setUserOpen((v) => !v)}
                  className={cn(
                    "flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm transition-all",
                    userOpen
                      ? "border-slate-300 bg-slate-50 text-slate-900"
                      : "border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-900"
                  )}
                >
                  <span className="flex size-7 items-center justify-center rounded-full bg-slate-900 text-xs font-medium text-white">
                    {user.username?.slice(0, 1).toUpperCase() ?? "?"}
                  </span>
                  <span className="hidden max-w-[100px] truncate text-sm font-medium lg:block">
                    {user.username}
                  </span>
                  <ChevronDown
                    className={cn(
                      "size-3.5 text-slate-400 transition-transform duration-200",
                      userOpen && "rotate-180"
                    )}
                  />
                </button>

                {userOpen && (
                  <div className="absolute right-0 top-full mt-2 w-64 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
                    {/* User Info */}
                    <div className="border-b border-slate-100 px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="flex size-9 items-center justify-center rounded-full bg-slate-900 text-sm font-medium text-white">
                          {user.username?.slice(0, 1).toUpperCase() ?? "?"}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            {user.fullName || user.username}
                          </p>
                          <p className="truncate text-xs text-slate-400">
                            @{user.username}
                          </p>
                        </div>
                      </div>


                      <div className="mt-2 space-y-1">
                        {user.telegramId && (
                          <div className="flex items-center gap-1.5 text-xs text-slate-500">
                            <MessageCircle className="size-3 text-slate-400" />
                            <span className="tabular-nums">{user.telegramId}</span>
                          </div>
                        )}
                        {user.phone && (
                          <div className="flex items-center gap-1.5 text-xs text-slate-500">
                            <Phone className="size-3 text-slate-400" />
                            <span className="tabular-nums">{user.phone}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Menu */}
                    <div className="p-1">
                      <DropdownItem
                        href={`/user/${user.username}`}
                        icon={<User className="size-4" />}
                        label="Profilim"
                      />
                      <DropdownItem
                        href="/settings"
                        icon={<Settings className="size-4" />}
                        label="Sozlamalar"
                      />
                      <DropdownItem
                        href="/courses"
                        icon={<BookOpen className="size-4" />}
                        label="Kurslarim"
                      />

                      <div className="my-1 border-t border-slate-100" />

                      <button
                        onClick={() => {
                          setUserOpen(false);
                          logout();
                        }}
                        className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-red-600 transition-colors hover:bg-red-50"
                      >
                        <LogOut className="size-4" />
                        Chiqish
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="hidden rounded-md px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 sm:block"
              >
                Kirish
              </Link>
              <Link
                href="/login"
                className="flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
              >
                Boshlash
              </Link>
            </div>
          )}

          {/* Mobile Toggle */}
          <button
            onClick={() => setMobileOpen((v) => !v)}
            className="flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 md:hidden"
          >
            {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 md:hidden">
          <nav className="flex flex-col gap-0.5">
            {navLinks.map((link) => {
              const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-slate-100 text-slate-900"
                      : "text-slate-600 hover:bg-slate-50"
                  )}
                >
                  <link.icon className="size-5" strokeWidth={1.5} />
                  {link.label}
                </Link>
              );
            })}

            <div className="my-2 border-t border-slate-100" />

            {isAuthenticated && user ? (
              <>
                <div className="flex items-center gap-3 px-3 py-2">
                  <span className="flex size-8 items-center justify-center rounded-full bg-slate-900 text-sm font-medium text-white">
                    {user.username?.slice(0, 1).toUpperCase() ?? "?"}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-slate-900">{user.username}</p>
                    <p className="text-xs text-slate-400">@{user.username}</p>
                  </div>
                </div>
                <Link
                  href={`/user/${user.username}`}
                  className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
                >
                  <User className="size-5" />
                  Profilim
                </Link>
                <button
                  onClick={() => {
                    setMobileOpen(false);
                    logout();
                  }}
                  className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  <LogOut className="size-5" />
                  Chiqish
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="flex items-center justify-center gap-2 rounded-md bg-slate-900 py-2.5 text-sm font-medium text-white"
              >
                Kirish
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}

function DropdownItem({
  href,
  icon,
  label,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
    >
      <span className="text-slate-400">{icon}</span>
      {label}
    </Link>
  );
}