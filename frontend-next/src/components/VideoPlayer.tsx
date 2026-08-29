//
// Talab qilinadi: npm install hls.js
// Logotip: public/cfm_contest.webp (yoki .png) fayli mavjud bo'lishi kerak.
//
// Professional, minimal qora/oq dizaynli 16:9 video pleer. HLS (.m3u8) va
// oddiy MP4 manbalarni qo'llab-quvvatlaydi. YouTube uslubidagi progress-bar,
// volume, fullscreen boshqaruvi va logotip watermark bilan.
//
// KLAVIATURA BOSHQARUVI (YouTube-style):
//   Space / K      → Play/Pause
//   ← / J          → 5s / 10s orqaga
//   → / L          → 5s / 10s oldinga
//   ↑              → Ovoz +10%
//   ↓              → Ovoz -10%
//   M              → Mute/Unmute
//   F              → Fullscreen toggle
//   0 - 9          → 0% - 90% ga o'tish

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Image from "next/image";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize,
  Minimize,
  Loader2,
  SkipBack,
  SkipForward,
} from "lucide-react";

interface VideoPlayerProps {
  src: string;
  poster?: string | null;
  title?: string;
  logoPosition?: "top-left" | "top-right";
  logoSrc?: string;
}

export function VideoPlayer({
  src,
  poster,
  title,
  logoPosition = "top-right",
  logoSrc = "/cfm_logo.webp",
}: VideoPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [showPoster, setShowPoster] = useState(true);
  const [paused, setPaused] = useState(true);
  const [loading, setLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.9);
  const [muted, setMuted] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(false);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [hoverPos, setHoverPos] = useState(0);
  const [actionIcon, setActionIcon] = useState<React.ReactNode | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const actionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ---------- HLS init ---------- */
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;
    let hls: import("hls.js").default | null = null;

    (async () => {
      if (src.includes(".m3u8")) {
        const HlsMod = (await import("hls.js")).default;
        if (HlsMod.isSupported()) {
          hls = new HlsMod({ enableWorker: true, lowLatencyMode: true });
          hls.loadSource(src);
          hls.attachMedia(video);
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
          video.src = src;
        }
      } else {
        video.src = src;
      }
    })();

    return () => {
      hls?.destroy();
    };
  }, [src]);

  /* ---------- Keyboard shortcuts ---------- */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const video = videoRef.current;
      if (!video || !containerRef.current) return;

      // Agar input/textarea fokusda bo'lsa, e'tibor bermaymiz
      const active = document.activeElement;
      if (
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement
      )
        return;

      // Container ko'rinmas yoki sahifada juda uzoqda bo'lsa
      const rect = containerRef.current.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;

      switch (e.key.toLowerCase()) {
        case " ":
        case "k":
          e.preventDefault();
          togglePlay();
          flashAction(paused ? <Play className="size-8" /> : <Pause className="size-8" />);
          break;
        case "arrowleft":
          e.preventDefault();
          seekDelta(-5);
          flashAction(<SkipBack className="size-8" />);
          break;
        case "j":
          e.preventDefault();
          seekDelta(-10);
          flashAction(<SkipBack className="size-8" />);
          break;
        case "arrowright":
          e.preventDefault();
          seekDelta(5);
          flashAction(<SkipForward className="size-8" />);
          break;
        case "l":
          e.preventDefault();
          seekDelta(10);
          flashAction(<SkipForward className="size-8" />);
          break;
        case "arrowup":
          e.preventDefault();
          changeVolumeDelta(0.1);
          break;
        case "arrowdown":
          e.preventDefault();
          changeVolumeDelta(-0.1);
          break;
        case "m":
          e.preventDefault();
          toggleMute();
          flashAction(muted ? <Volume2 className="size-8" /> : <VolumeX className="size-8" />);
          break;
        case "f":
          e.preventDefault();
          toggleFullscreen();
          break;
        case "0":
        case "1":
        case "2":
        case "3":
        case "4":
        case "5":
        case "6":
        case "7":
        case "8":
        case "9":
          e.preventDefault();
          seekPercent(parseInt(e.key, 10) * 10);
          break;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [paused, muted]);

  /* ---------- Helpers ---------- */
  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (showPoster) {
      setShowPoster(false);
      video.play().catch(() => {});
      return;
    }
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  }, [showPoster]);

  function seekDelta(delta: number) {
    const v = videoRef.current;
    if (!v || !duration) return;
    v.currentTime = Math.max(0, Math.min(duration, v.currentTime + delta));
  }

  function seekPercent(percent: number) {
    const v = videoRef.current;
    if (!v || !duration) return;
    v.currentTime = (duration * percent) / 100;
  }

  function changeVolumeDelta(delta: number) {
    const v = videoRef.current;
    if (!v) return;
    const next = Math.max(0, Math.min(1, v.volume + delta));
    v.volume = next;
    v.muted = false;
    setVolume(next);
    setMuted(false);
  }

  function flashAction(icon: React.ReactNode) {
    setActionIcon(icon);
    if (actionTimer.current) clearTimeout(actionTimer.current);
    actionTimer.current = setTimeout(() => setActionIcon(null), 600);
  }

  function onTimeUpdate() {
    const v = videoRef.current;
    if (!v) return;
    setCurrentTime(v.currentTime);
    setDuration(v.duration || 0);
  }

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    const v = videoRef.current;
    if (!v || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    v.currentTime = ratio * duration;
  }

  function onProgressHover(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setHoverPos(e.clientX - rect.left);
    setHoverTime(ratio * duration);
  }

  function changeVolume(e: React.MouseEvent<HTMLDivElement>) {
    const v = videoRef.current;
    if (!v) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    v.volume = ratio;
    v.muted = false;
    setVolume(ratio);
    setMuted(false);
  }

  function toggleMute() {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
  }

  function toggleFullscreen() {
    const el = containerRef.current;
    if (!el) return;
    if (!document.fullscreenElement) el.requestFullscreen().catch(() => {});
    else document.exitFullscreen().catch(() => {});
  }

  useEffect(() => {
    const handler = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  function formatTime(s: number) {
    if (!s || isNaN(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec < 10 ? "0" : ""}${sec}`;
  }

  function onMouseMove() {
    setShowControls(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setShowControls(false), 2500);
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      ref={containerRef}
      onMouseMove={onMouseMove}
      onClick={togglePlay}
      className="group relative aspect-video w-full cursor-pointer select-none overflow-hidden rounded-xl bg-black"
    >
      {/* Poster */}
      {poster && (
        <div
          className={`absolute inset-0 bg-cover bg-center transition-opacity duration-500 ${
            showPoster ? "opacity-100" : "pointer-events-none opacity-0"
          }`}
          style={{ backgroundImage: `url(${poster})` }}
        />
      )}

      {/* Logo watermark */}
      <div
        className={`pointer-events-none absolute z-20 ${
          logoPosition === "top-right" ? "right-3 top-3" : "left-3 top-3"
        }`}
      >
        <Image
          src={logoSrc}
          alt="CFM"
          width={36}
          height={36}
          className="rounded opacity-80 drop-shadow"
          unoptimized
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center">
          <Loader2 className="size-9 animate-spin text-white/80" />
        </div>
      )}

      {/* Action feedback (keyboard) */}
      {actionIcon && (
        <div className="absolute inset-0 z-[15] flex items-center justify-center">
          <div className="flex size-16 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-sm">
            {actionIcon}
          </div>
        </div>
      )}

      {/* Play button */}
      {(showPoster || paused) && !loading && !actionIcon && (
        <div className="absolute inset-0 z-10 flex items-center justify-center">
          <span className="flex size-16 items-center justify-center rounded-full bg-white/20 ring-1 ring-white/40 backdrop-blur-sm transition group-hover:scale-105 group-hover:bg-white/30 sm:size-20">
            <Play className="ml-1 size-8 text-white sm:size-9" fill="white" />
          </span>
        </div>
      )}

      <video
        ref={videoRef}
        className="h-full w-full object-contain"
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onTimeUpdate}
        onPlay={() => {
          setPaused(false);
          setShowPoster(false);
        }}
        onPause={() => setPaused(true)}
        onWaiting={() => setLoading(true)}
        onCanPlay={() => setLoading(false)}
      />

      {/* Controls */}
      <div
        onClick={(e) => e.stopPropagation()}
        className={`absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/85 via-black/40 to-transparent px-3 pb-3 pt-8 transition-opacity duration-300 sm:px-4 ${
          showControls || paused ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        }`}
      >
        {/* Progress bar */}
        <div
          onClick={seek}
          onMouseMove={onProgressHover}
          onMouseLeave={() => setHoverTime(null)}
          className="group/bar relative mb-2.5 h-1.5 cursor-pointer rounded-full bg-white/25 transition-all hover:h-2"
        >
          <div
            className="relative h-full rounded-full bg-red-600"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute right-0 top-1/2 size-3.5 -translate-y-1/2 translate-x-1/2 rounded-full bg-red-600 opacity-0 shadow transition group-hover/bar:opacity-100" />
          </div>

          {/* Hover time tooltip */}
          {hoverTime !== null && duration > 0 && (
            <div
              className="pointer-events-none absolute -top-9 rounded bg-black/80 px-1.5 py-0.5 text-[11px] font-medium text-white"
              style={{ left: `${Math.max(0, Math.min(100, (hoverPos / (containerRef.current?.clientWidth || 1)) * 100))}%`, transform: "translateX(-50%)" }}
            >
              {formatTime(hoverTime)}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button onClick={togglePlay} className="text-white/90 hover:text-white">
            {paused ? (
              <Play className="size-5" fill="currentColor" />
            ) : (
              <Pause className="size-5" fill="currentColor" />
            )}
          </button>

          <span className="font-mono text-xs text-white/80">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          <div className="hidden items-center gap-2 sm:flex">
            <button onClick={toggleMute} className="text-white/90 hover:text-white">
              {muted || volume === 0 ? (
                <VolumeX className="size-4" />
              ) : (
                <Volume2 className="size-4" />
              )}
            </button>
            <div onClick={changeVolume} className="h-1 w-16 cursor-pointer rounded-full bg-white/25">
              <div
                className="h-full rounded-full bg-white"
                style={{ width: `${muted ? 0 : volume * 100}%` }}
              />
            </div>
          </div>

          <span className="flex-1" />

          {title && (
            <span className="hidden max-w-[40%] truncate text-xs text-white/70 md:inline">
              {title}
            </span>
          )}

          <button onClick={toggleFullscreen} className="text-white/90 hover:text-white">
            {fullscreen ? <Minimize className="size-4" /> : <Maximize className="size-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}