"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, Sparkles, Trophy, Star, Gem, Award, TrendingUp } from "lucide-react";

/* ================================================================
   XP BUTTON COMPONENT - SIMPLE & POWERFUL
   ================================================================ */

interface XPButtonProps {
  /** Qo'shiladigan XP miqdori */
  xpAmount: number;
  /** Tugma o'lchami */
  size?: "sm" | "md" | "lg";
  /** Qo'shimcha classlar */
  className?: string;
  /** XP qo'shilganda chaqiriladigan funksiya */
  onCollect?: (amount: number) => void;
}

export function XPButton({ 
  xpAmount, 
  size = "md", 
  className = "",
  onCollect 
}: XPButtonProps) {
  const [isAnimating, setIsAnimating] = useState(false);
  const [showFloatingText, setShowFloatingText] = useState(false);
  const [floatingTexts, setFloatingTexts] = useState<{ id: number; x: number; y: number; text: string }[]>([]);
  const [particles, setParticles] = useState<{ id: number; x: number; y: number; size: number; color: string; delay: number }[]>([]);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const textIdCounter = useRef(0);

  // Size configurations
  const sizeConfig = {
    sm: {
      button: "px-4 py-2 text-sm",
      icon: "w-4 h-4",
      xpText: "text-base",
      glow: "w-12 h-12",
    },
    md: {
      button: "px-6 py-3 text-base",
      icon: "w-5 h-5",
      xpText: "text-xl",
      glow: "w-16 h-16",
    },
    lg: {
      button: "px-8 py-4 text-lg",
      icon: "w-6 h-6",
      xpText: "text-2xl",
      glow: "w-20 h-20",
    },
  };

  const config = sizeConfig[size];

  // Collect XP
  const handleCollect = (e: React.MouseEvent) => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    setShowFloatingText(true);
    
    const rect = buttonRef.current?.getBoundingClientRect();
    if (rect) {
      // Create floating text particles
      const newTexts = [];
      const emojis = ["✨", "⚡", "🌟", "💫", "⭐", "🔥"];
      for (let i = 0; i < 6; i++) {
        newTexts.push({
          id: textIdCounter.current++,
          x: rect.left + rect.width / 2 + (Math.random() - 0.5) * 80,
          y: rect.top - 20 + (Math.random() - 0.5) * 40,
          text: emojis[Math.floor(Math.random() * emojis.length)],
        });
      }
      // Add XP text
      newTexts.push({
        id: textIdCounter.current++,
        x: rect.left + rect.width / 2,
        y: rect.top - 30,
        text: `+${xpAmount} XP`,
      });
      setFloatingTexts(newTexts);

      // Create particles
      const newParticles = [];
      const colors = ["#fbbf24", "#f59e0b", "#fcd34d", "#fde68a", "#fbbf24", "#f59e0b"];
      for (let i = 0; i < 20; i++) {
        newParticles.push({
          id: i,
          x: (Math.random() - 0.5) * 120,
          y: (Math.random() - 0.5) * 120 - 40,
          size: 4 + Math.random() * 6,
          color: colors[Math.floor(Math.random() * colors.length)],
          delay: Math.random() * 0.3,
        });
      }
      setParticles(newParticles);
    }

    // Callback - faqat XP miqdorini qaytaradi
    if (onCollect) {
      onCollect(xpAmount);
    }

    // Reset
    setTimeout(() => {
      setIsAnimating(false);
      setShowFloatingText(false);
      setFloatingTexts([]);
      setParticles([]);
    }, 2000);
  };

  return (
    <div className="relative inline-block">
      {/* Floating Texts */}
      <AnimatePresence>
        {showFloatingText && floatingTexts.map((ft) => (
          <motion.div
            key={ft.id}
            initial={{ opacity: 1, y: 0, scale: 0.3 }}
            animate={{ 
              opacity: 0, 
              y: -100 - Math.random() * 60,
              x: ft.x + (Math.random() - 0.5) * 60,
              scale: 1.5 + Math.random() * 0.5,
            }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            className={`fixed pointer-events-none z-[100] font-bold ${
              ft.text.includes("XP") ? "text-4xl text-yellow-400" : "text-3xl"
            }`}
            style={{ 
              left: ft.x, 
              top: ft.y,
              textShadow: "0 0 20px rgba(251, 191, 36, 0.5)",
            }}
          >
            {ft.text}
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Particles */}
      <AnimatePresence>
        {isAnimating && particles.map((p) => (
          <motion.div
            key={p.id}
            initial={{ x: 0, y: 0, scale: 0, opacity: 1 }}
            animate={{
              x: p.x,
              y: p.y,
              scale: 1,
              opacity: 0,
            }}
            transition={{
              duration: 0.8 + Math.random() * 0.4,
              delay: p.delay,
              ease: "easeOut",
            }}
            className="absolute top-1/2 left-1/2 pointer-events-none rounded-full"
            style={{
              width: p.size,
              height: p.size,
              background: p.color,
              boxShadow: `0 0 20px ${p.color}`,
            }}
          />
        ))}
      </AnimatePresence>

      {/* Main Button */}
      <motion.button
        ref={buttonRef}
        onClick={handleCollect}
        disabled={isAnimating}
        className={`
          relative overflow-hidden group
          flex items-center gap-3
          rounded-2xl font-bold
          bg-gradient-to-r from-yellow-400 via-amber-500 to-yellow-400
          bg-[length:200%_100%]
          text-white
          shadow-lg shadow-yellow-500/30
          hover:shadow-xl hover:shadow-yellow-500/50
          transition-all duration-300
          ${config.button}
          ${className}
          ${isAnimating ? "cursor-default" : "cursor-pointer"}
        `}
        style={{
          backgroundSize: "200% 100%",
          animation: isAnimating ? "shimmer 0.8s ease-in-out infinite" : "none",
        }}
        whileHover={!isAnimating ? { scale: 1.05 } : {}}
        whileTap={!isAnimating ? { scale: 0.95 } : {}}
      >
        {/* Glow */}
        <motion.div
          className={`absolute rounded-full bg-yellow-300/50 blur-xl ${config.glow}`}
          animate={isAnimating ? { 
            scale: [1, 1.5, 1],
            opacity: [0.3, 0.8, 0.3],
          } : {
            scale: [1, 1.1, 1],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={isAnimating ? {
            duration: 0.8,
            repeat: Infinity,
          } : {
            duration: 2,
            repeat: Infinity,
          }}
          style={{ 
            left: "50%", 
            top: "50%", 
            transform: "translate(-50%, -50%)",
            width: config.glow,
            height: config.glow,
          }}
        />

        {/* Icon */}
        <motion.div
          className="relative z-10"
          animate={isAnimating ? {
            scale: [1, 1.6, 1],
            rotate: [0, 20, -20, 0],
          } : {
            scale: [1, 1.15, 1],
            rotate: [0, 8, -8, 0],
          }}
          transition={isAnimating ? {
            duration: 0.7,
            repeat: Infinity,
          } : {
            duration: 2,
            repeat: Infinity,
          }}
        >
          <Zap className={`${config.icon} text-white drop-shadow-lg`} />
        </motion.div>

        {/* XP Text */}
        <motion.span
          className={`relative z-10 font-bold ${config.xpText}`}
          animate={isAnimating ? {
            scale: [1, 1.2, 1],
          } : {}}
          transition={{ duration: 0.5, repeat: isAnimating ? Infinity : 0 }}
        >
          +{xpAmount} XP
        </motion.span>

        {/* Lightning flashes */}
        {isAnimating && (
          <>
            <motion.div
              className="absolute inset-0 pointer-events-none"
              animate={{ opacity: [0, 0.6, 0] }}
              transition={{ duration: 0.15, repeat: 6, repeatDelay: 0.15 }}
            >
              <div className="absolute top-0 left-1/4 w-0.5 h-full bg-white/60 blur-sm" />
              <div className="absolute top-0 right-1/4 w-0.5 h-full bg-yellow-300/40 blur-sm" />
              <div className="absolute top-0 left-1/2 w-0.5 h-full bg-white/80 blur-sm" />
            </motion.div>

            {/* Starburst effect */}
            <motion.div
              className="absolute inset-0 pointer-events-none"
              animate={{ 
                opacity: [0, 1, 0],
                scale: [0.8, 1.2, 0.8],
              }}
              transition={{ duration: 0.4, repeat: 3 }}
            >
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32">
                {[...Array(8)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute top-1/2 left-1/2 w-1 h-8 bg-white/40 rounded-full"
                    style={{
                      transform: `rotate(${i * 45}deg) translateY(-50%)`,
                      transformOrigin: "center bottom",
                    }}
                  />
                ))}
              </div>
            </motion.div>
          </>
        )}
      </motion.button>
    </div>
  );
}

/* ================================================================
   REVIEW PAGE INTEGRATION - XP qismi
   ================================================================ */

// ReviewPage dagi XP qismini quyidagicha yangilang:

/*
<div className="flex flex-wrap items-center gap-3">
  <XPButton 
    xpAmount={review.xp_earned} 
    size="md"
    onCollect={(amount) => {
      // Faqat konsolga chiqarish yoki state yangilash
      console.log(`+${amount} XP collected!`);
      // Agar state ishlatmoqchi bo'lsangiz:
      // setCollectedXP(prev => prev + amount);
    }}
  />
  {passed && (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-700"
    >
      <Gift className="h-4 w-4" />
      +50 Bonus
    </motion.div>
  )}
  <motion.div
    whileHover={{ scale: 1.05 }}
    className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600"
  >
    <Award className="h-4 w-4" />
    {review.score} ball
  </motion.div>
</div>
*/

/* ================================================================
   STANDALONE EXAMPLE
   ================================================================ */

export function XPCollectExample() {
  const [totalXP, setTotalXP] = useState(0);
  const [logs, setLogs] = useState<{ amount: number; time: string }[]>([]);

  const handleCollect = (amount: number) => {
    setTotalXP(prev => prev + amount);
    setLogs(prev => [
      { amount, time: new Date().toLocaleTimeString() },
      ...prev.slice(0, 9)
    ]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-white p-8">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center justify-center gap-3">
            <Trophy className="text-amber-500" />
            XP Yig'ish
            <Trophy className="text-amber-500" />
          </h1>
          <p className="text-slate-500">Tugmani bosing va XP yig'ing!</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
          {/* Total XP */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-3">
              <TrendingUp className="text-emerald-500" />
              <span className="text-sm text-slate-500">Jami XP</span>
            </div>
            <motion.div
              key={totalXP}
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-5xl font-bold text-slate-900"
            >
              {totalXP.toLocaleString()}
            </motion.div>
            <div className="mt-1 flex items-center justify-center gap-1">
              <Star className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-slate-400">
                Level {Math.floor(totalXP / 100) + 1}
              </span>
            </div>
          </div>

          {/* XP Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-8">
            <XPButton xpAmount={10} size="sm" onCollect={handleCollect} />
            <XPButton xpAmount={25} size="sm" onCollect={handleCollect} />
            <XPButton xpAmount={50} size="md" onCollect={handleCollect} />
            <XPButton xpAmount={100} size="lg" onCollect={handleCollect} />
            <XPButton xpAmount={250} size="lg" onCollect={handleCollect} />
          </div>

          {/* Logs */}
          <div className="border-t border-slate-200 pt-4">
            <p className="text-sm font-medium text-slate-600 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              So'nggi yutuqlar
            </p>
            {logs.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">
                Hali XP yig'ilmagan. Tugmani bosing!
              </p>
            ) : (
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {logs.map((item, i) => (
                  <motion.div
                    key={i}
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-slate-50 transition-colors"
                  >
                    <span className="flex items-center gap-2 text-sm">
                      <span className="text-amber-500">✦</span>
                      <span className="font-medium text-slate-700">+{item.amount} XP</span>
                    </span>
                    <span className="text-xs text-slate-400">{item.time}</span>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// STYLES - app/globals.css ga qo'shing
// ============================================================
/*
@keyframes shimmer {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

@keyframes sparkle {
  0%, 100% { opacity: 0; transform: scale(0); }
  50% { opacity: 1; transform: scale(1); }
}
*/