"use client";

import { useEffect, useRef } from "react";

export default function BackgroundCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = 1;
    const particles: Array<{ x: number; y: number; vx: number; vy: number; radius: number; opacity: number }> = [];
    const pointer = { x: 0, y: 0, active: false };

    const resize = () => {
      dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      particles.length = 0;
      const count = Math.min(90, Math.max(40, Math.floor(width / 24)));
      for (let i = 0; i < count; i += 1) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          radius: Math.random() * 1.8 + 0.6,
          opacity: 0.3 + Math.random() * 0.55,
        });
      }
    };

    const onPointerMove = (event: PointerEvent) => {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      pointer.active = true;
    };

    const onPointerLeave = () => {
      pointer.active = false;
    };

    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);

      // Pure Black Canvas Background
      ctx.fillStyle = "#000000";
      ctx.fillRect(0, 0, width, height);

      // Subtle top center white glow
      const topGlow = ctx.createRadialGradient(width * 0.5, 0, 0, width * 0.5, 0, width * 0.6);
      topGlow.addColorStop(0, "rgba(255, 255, 255, 0.07)");
      topGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = topGlow;
      ctx.fillRect(0, 0, width, height);

      particles.forEach((particle, index) => {
        particle.x += particle.vx;
        particle.y += particle.vy;

        if (particle.x < -10 || particle.x > width + 10) particle.vx *= -1;
        if (particle.y < -10 || particle.y > height + 10) particle.vy *= -1;

        if (pointer.active) {
          const dx = pointer.x - particle.x;
          const dy = pointer.y - particle.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 160) {
            const force = (160 - dist) / 160;
            particle.x -= dx * force * 0.002;
            particle.y -= dy * force * 0.002;
          }
        }

        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`;
        ctx.fill();

        // White-toned connection lines
        for (let j = index + 1; j < particles.length; j += 1) {
          const other = particles[j];
          const dx = particle.x - other.x;
          const dy = particle.y - other.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 110) {
            ctx.beginPath();
            ctx.moveTo(particle.x, particle.y);
            ctx.lineTo(other.x, other.y);
            ctx.strokeStyle = `rgba(255, 255, 255, ${0.03 + (1 - dist / 110) * 0.12})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      });

      // Subtle grid lines
      ctx.save();
      ctx.globalAlpha = 0.04;
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 0.5;
      for (let i = 0; i < height; i += 70) {
        ctx.beginPath();
        ctx.moveTo(0, i + ((time / 2000) % 70));
        ctx.lineTo(width, i + ((time / 2000) % 70));
        ctx.stroke();
      }
      ctx.restore();

      requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerleave", onPointerLeave);
    const frame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
    };
  }, []);

  return <canvas ref={canvasRef} className="background-canvas" aria-hidden="true" />;
}
