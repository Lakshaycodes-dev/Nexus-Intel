"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

type Tone = {
  a: string;
  b: string;
  c: string;
  kicker: string;
};

type FlickCard = {
  tone: Tone;
  kicker: string;
  title: string;
  description: string;
};

const cards: FlickCard[] = [
  {
    tone: { a: "99 102 241", b: "34 211 238", c: "139 92 246", kicker: "#4f46e5" },
    kicker: "Signal layer",
    title: "Off-Site Web Discovery",
    description:
      "We follow the story beyond the homepage — press, review sites, changelogs, communities, and the places your competitors get talked about.",
  },
  {
    tone: { a: "37 99 235", b: "6 182 212", c: "99 102 241", kicker: "#1d4ed8" },
    kicker: "Interface layer",
    title: "Dynamic Switch Interaction",
    description:
      "Annual toggles, hidden accordions, gated plan details. Nexus navigates the interface the way a buyer would.",
  },
  {
    tone: { a: "16 185 129", b: "20 184 166", c: "132 204 22", kicker: "#047857" },
    kicker: "Extraction layer",
    title: "Clean Extraction",
    description:
      "No menus, trackers, or duplicated markup. Just the commercial signal, normalized into a structure your team can trust.",
  },
  {
    tone: { a: "245 158 11", b: "251 113 133", c: "139 92 246", kicker: "#b45309" },
    kicker: "Matrix layer",
    title: "Structured AI Matrices",
    description:
      "Pricing, features, positioning, and support SLAs resolved into one comparable source of truth — ready for the boardroom.",
  },
  {
    tone: { a: "217 70 239", b: "99 102 241", c: "34 211 238", kicker: "#a21caf" },
    kicker: "Live layer",
    title: "Live Signal Monitoring",
    description:
      "Every pricing move, product launch, and off-site mention tracked in real time across your market.",
  },
  {
    tone: { a: "101 163 13", b: "20 184 166", c: "245 158 11", kicker: "#4d7c0f" },
    kicker: "Briefing layer",
    title: "Executive Briefs",
    description:
      "The change, what it means, and what to do next — written the moment it matters.",
  },
];

const AUTOPLAY_MS = 3800;
const TOTAL = cards.length;

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function rgba(tone: string, alpha: number) {
  return `rgba(${tone.split(" ").join(", ")}, ${alpha})`;
}

function poseFor(distance: number) {
  const abs = Math.abs(distance);
  const sign = Math.sign(distance);

  return {
    x: sign * Math.pow(abs, 0.7) * 52,
    y: abs * 5,
    z: -abs * 140,
    rotateY: -sign * Math.min(abs, 3) * 18,
    rotateZ: sign * abs * 2.2,
    scale: 1 - abs * 0.04,
    shade: distance === 0 ? 0 : Math.min(0.14 + abs * 0.08, 0.4),
    hidden: abs > 3,
  };
}

function CardArt() {
  return (
    <div className="flick-art" aria-hidden="true">
      <span className="flick-haze" />
      <span className="flick-grid" />
      <span className="flick-ring flick-ring-one" />
      <span className="flick-ring flick-ring-two" />
      <svg className="flick-trace" viewBox="0 0 200 120" preserveAspectRatio="none">
        <path d="M0 86C22 80 30 44 52 56c24 13 32-33 56-24 24 9 34-20 60-12 16 5 24-5 32-12" />
        <path d="M0 104c26-5 40-27 62-20 21 7 32-28 56-21 23 6 36-19 59-14 10 2 17-2 23-6" />
      </svg>
      <span className="flick-panel flick-panel-a">
        <i />
        <i />
        <i />
      </span>
      <span className="flick-panel flick-panel-b">
        <i />
        <i />
      </span>
      <span className="flick-node flick-node-a" />
      <span className="flick-node flick-node-b" />
      <span className="flick-node flick-node-c" />
      <span className="flick-grain" />
    </div>
  );
}

export function FlickCards() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [dragging, setDragging] = useState(false);
  const reducedMotion = useReducedMotion();

  const navigate = useCallback((direction: number) => {
    setActive((current) => (current + direction + TOTAL) % TOTAL);
  }, []);

  useEffect(() => {
    if (reducedMotion || paused || dragging) return;

    const timer = window.setTimeout(() => {
      navigate(1);
    }, AUTOPLAY_MS);

    return () => window.clearTimeout(timer);
  }, [active, dragging, navigate, paused, reducedMotion]);

  function offsetFor(index: number) {
    let distance = index - active;
    const half = TOTAL / 2;

    if (distance > half) distance -= TOTAL;
    if (distance < -half) distance += TOTAL;

    return distance;
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      navigate(-1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      navigate(1);
    }
  }

  return (
    <div
      className="flick-deck"
      onPointerEnter={() => setPaused(true)}
      onPointerLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      <div
        className="flick-ambient"
        aria-hidden="true"
        style={{
          background: `radial-gradient(circle, ${rgba(cards[active].tone.a, 0.28)} 0%, ${rgba(
            cards[active].tone.b,
            0.14,
          )} 45%, transparent 72%)`,
        }}
      />
      <div className="flick-grid-bg" aria-hidden="true" />
      <div className="flick-vignette" aria-hidden="true" />

      <div className="flick-topbar">
        <div className="flick-brand">
          <span className="flick-brand-dot" aria-hidden="true" />
          <span>Nexus Intel</span>
          <span className="flick-brand-divider" aria-hidden="true" />
          <span className="flick-brand-sub">Capability deck</span>
        </div>
        <div className="flick-counter">
          <span>{pad(active + 1)}</span>
          <span className="dim"> / {pad(TOTAL)}</span>
        </div>
      </div>

      <button
        type="button"
        className="flick-nav flick-nav-prev"
        aria-label="Previous capability"
        onClick={() => navigate(-1)}
      >
        <ChevronLeft aria-hidden="true" />
      </button>
      <button
        type="button"
        className="flick-nav flick-nav-next"
        aria-label="Next capability"
        onClick={() => navigate(1)}
      >
        <ChevronRight aria-hidden="true" />
      </button>

      <div
        className="flick-stage"
        role="region"
        aria-roledescription="carousel"
        aria-label="Nexus Intel capability deck"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {cards.map((card, index) => {
          const distance = offsetFor(index);
          const pose = poseFor(distance);
          const isFront = distance === 0;

          return (
            <motion.article
              key={card.title}
              className={cn("flick-card", isFront && "is-front")}
              style={
                {
                  "--a": card.tone.a,
                  "--b": card.tone.b,
                  "--c": card.tone.c,
                  zIndex: 20 - Math.abs(distance) * 2,
                } as CSSProperties
              }
              initial={{ opacity: 0, y: 90, scale: 0.92 }}
              animate={{
                x: `${pose.x}%`,
                y: pose.y,
                z: pose.z,
                rotateY: pose.rotateY,
                rotateZ: pose.rotateZ,
                scale: pose.scale,
                opacity: pose.hidden ? 0 : 1,
              }}
              transition={{
                duration: reducedMotion ? 0 : 0.9,
                ease: [0.16, 1, 0.3, 1],
              }}
              drag={isFront ? "x" : false}
              dragSnapToOrigin
              dragElastic={0.18}
              dragMomentum={false}
              onDragStart={() => {
                setDragging(true);
                setPaused(true);
              }}
              onDragEnd={(_, info) => {
                setDragging(false);

                const threshold = 70;

                if (info.offset.x < -threshold || info.velocity.x < -450) {
                  navigate(1);
                } else if (info.offset.x > threshold || info.velocity.x > 450) {
                  navigate(-1);
                }
              }}
              aria-roledescription="slide"
              aria-label={`${index + 1} of ${TOTAL}: ${card.title}`}
              aria-hidden={!isFront}
            >
              <CardArt />
              <div
                className="flick-shade"
                aria-hidden="true"
                style={{ opacity: pose.shade }}
              />
              <div className="flick-ui" style={{ opacity: isFront ? 1 : 0 }}>
                <div className="flick-meta">
                  <span>Capability {pad(index + 1)}</span>
                  <span>Nexus Intel</span>
                </div>
                <div className="flick-copy">
                  <span className="flick-kicker" style={{ color: card.tone.kicker }}>
                    {card.kicker}
                  </span>
                  <h3 className="flick-name">{card.title}</h3>
                  <p className="flick-desc">{card.description}</p>
                </div>
                <Link
                  href="/dashboard"
                  className="flick-cta"
                  tabIndex={isFront ? 0 : -1}
                  draggable={false}
                  onPointerDown={(event) => event.stopPropagation()}
                >
                  <span>Get this product</span>
                  <ArrowUpRight aria-hidden="true" />
                </Link>
              </div>
            </motion.article>
          );
        })}
      </div>

      <div className="flick-progress" aria-hidden="true">
        {cards.map((card, index) => (
          <button
            key={card.title}
            type="button"
            className={cn("flick-dot", index === active && "active")}
            tabIndex={-1}
            aria-label={`Go to ${card.title}`}
            onClick={() => setActive(index)}
          />
        ))}
      </div>

      <div className="flick-bottombar" aria-hidden="true">
        <span>
          Drag the front card <em>·</em> Arrow keys <em>·</em> Auto
        </span>
        <span>Built for teams that move first</span>
      </div>

      <div className="sr-only" aria-live="polite">
        {cards[active].title}
      </div>
    </div>
  );
}
