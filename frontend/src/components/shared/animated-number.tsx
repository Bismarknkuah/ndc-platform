"use client";

import { useEffect, useRef } from "react";
import { motion, useMotionValue, useTransform, animate, useInView } from "framer-motion";

/**
 * Counts up from 0 to `value` when it first scrolls into view - used on
 * dashboard/analytics stat cards so a page full of numbers doesn't just
 * pop in inert, without turning every screen into a distracting
 * animation demo. Respects `prefers-reduced-motion` by snapping
 * straight to the final value instead of animating.
 */
export function AnimatedNumber({
  value,
  duration = 0.8,
  formatter,
  className,
}: {
  value: number;
  duration?: number;
  formatter?: (n: number) => string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-10% 0px" });
  const motionValue = useMotionValue(0);
  const rounded = useTransform(motionValue, (latest) =>
    formatter ? formatter(Math.round(latest)) : Math.round(latest).toLocaleString(),
  );

  useEffect(() => {
    if (!isInView) return;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      motionValue.set(value);
      return;
    }
    const controls = animate(motionValue, value, { duration, ease: "easeOut" });
    return () => controls.stop();
  }, [isInView, value, duration, motionValue]);

  return (
    <motion.span ref={ref} className={className}>
      {rounded}
    </motion.span>
  );
}
