import { FileQuestion } from "lucide-react";
import { VideoPlayer } from "@/components/VideoPlayer";
import type { ContestVideo } from "@/lib/contests/types";

export function ContestVideoPlayer({
  video,
  title,
  dark = false,
}: {
  video?: ContestVideo | null;
  title: string;
  dark?: boolean;
}) {
  const src = video?.hls_url || video?.video || null;

  // intro_video umuman biriktirilmagan
  if (!video || (!src && !video.thumbnail)) {
    return (
      <div
        className={`flex aspect-video items-center justify-center rounded-xl border ${
          dark
            ? "border-white/10 bg-white/5 text-white/30"
            : "border-[#E4E1D9] bg-[#F5F4EF] text-[#C8C4B8]"
        }`}
      >
        <FileQuestion size={32} strokeWidth={1.5} aria-hidden />
      </div>
    );
  }

  // Thumbnail bor, lekin hali oqim (hls_url/video) tayyorlanmagan
  if (!src) {
    return (
      <div className="relative aspect-video overflow-hidden rounded-xl border border-[#E4E1D9] bg-[#F5F4EF]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={video.thumbnail!} alt="" className="h-full w-full object-cover opacity-70" />
        <span className="absolute inset-0 flex items-center justify-center bg-black/30 text-sm text-white/85">
          Video tayyorlanmoqda
        </span>
      </div>
    );
  }

  return <VideoPlayer src={src} poster={video.thumbnail} title={title} />;
}