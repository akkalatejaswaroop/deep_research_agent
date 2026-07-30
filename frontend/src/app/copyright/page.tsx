"use client";
import { motion } from "framer-motion";

/**
 * Copyright & Legal Information page – premium styled content describing copyright
 * laws, the need for permission, and the consequences of unauthorized copying.
 * Uses the same design tokens and motion principles as the rest of the app.
 */
export default function CopyrightPage() {
  return (
    <section className="relative min-h-screen bg-[var(--surface)] px-6 py-12 text-[var(--text-1)] sm:px-8 lg:px-16">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto max-w-3xl text-center"
      >
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-[var(--brand-primary)] sm:text-4xl lg:text-5xl">
          © {new Date().getFullYear()} REX – Copyright Notice
        </h1>
        <p className="mt-4 max-w-2xl text-base text-[var(--text-2)] sm:text-lg leading-relaxed">
          All content, designs, and code displayed on this platform are protected by
          applicable copyright, trademark, and intellectual‑property laws.
        </p>
      </motion.header>

      {/* Main Content */}
      <motion.article
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto mt-12 max-w-3xl space-y-8 text-[var(--text-2)]"
      >
        <section>
          <h2 className="text-xl font-display font-bold text-[var(--brand-primary)]">
            Proper Use of Content
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            You may not reproduce, distribute, modify, or publicly display any
            part of this site without explicit written permission from the
            copyright holder. Unauthorized copying may result in legal action,
            including claims for damages, injunctions, and statutory penalties.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-display font-bold text-[var(--brand-primary)]">
            When Permission Is Required
          </h2>
          <ul className="mt-2 list-disc list-inside space-y-1 text-sm">
            <li>Re‑publishing or translating any article or visual asset.</li>
            <li>Embedding code snippets in external projects without attribution.</li>
            <li>Commercial use of our branding, logos, or UI components.</li>
            <li>Creating derivative works that compete with the original platform.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-display font-bold text-[var(--brand-primary)]">
            How to Request Permission &amp; Contact
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            For inquiries regarding licensing, partnership, or permission to reuse any REX technology, content, or intellectual assets, please contact us directly at <a href="mailto:tejaswaroopakkala@gmail.com" className="underline text-[var(--brand-primary)]">tejaswaroopakkala@gmail.com</a>.
          </p>
          <p className="mt-2 text-sm leading-relaxed">
            We will evaluate each request individually and respond within 5 business days. Please include a clear description of the intended scope, target audience, and duration of the proposed usage in your email.
          </p>
        </section>

        {/* REX Core Idea & Architecture Documentation */}
        <section className="border-t border-[var(--border)] pt-8">
          <h2 className="text-xl font-display font-bold text-[var(--brand-primary)]">
            About REX: Multi-Agent Deep Research Pipeline
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            REX (Recursive Exploration eXplorer) is a proprietary, self-improving multi-agent architecture engineered to automate complex academic, market, and technical research workflows. The core system operates across nine specialized pipeline phases, deploying cooperative agents to recursively search web indices, map credentials, extract semantically relevant text, resolve data discrepancies, and detect knowledge gaps.
          </p>
          <p className="mt-2 text-sm leading-relaxed">
            By executing a real-time telemetry audit, REX monitors information extraction confidence scores and enforces a strict 100% verifiable citation structure. The synthesized output is formulated with granular reference tracing to eliminate hallucinated assertions, presenting validated intelligence in a premium structured report.
          </p>
        </section>

        {/* Detailed Copyrights & Legal Information */}
        <section className="border-t border-[var(--border)] pt-8">
          <h2 className="text-xl font-display font-bold text-[var(--brand-primary)]">
            Copyright Protection &amp; Legal Framework
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            All code, structural designs, text content, telemetry assets, system visualizers, graphic styles, and algorithmic descriptions associated with REX are protected under local and international intellectual property treaties, including but not limited to:
          </p>
          <ul className="mt-2 list-disc list-inside space-y-2 text-sm">
            <li><strong>Title 17 of the United States Code (U.S. Copyright Act)</strong>: Protection against unauthorized reproduction, distribution, display, or creation of derivative works.</li>
            <li><strong>The Berne Convention for the Protection of Literary and Artistic Works</strong>: Enforcing automatic, international protection of REX's creative elements across 180+ member nations.</li>
            <li><strong>Digital Millennium Copyright Act (DMCA)</strong>: Immediate enforcement procedures and penalties for circumventing access control systems or copying online digital content without proper authorization.</li>
          </ul>
          <p className="mt-3 text-sm leading-relaxed text-[var(--accent-ember)] font-medium">
            Warning: Any copying, cloning, or decompiling of the multi-agent pipeline algorithms or styling assets without explicit written consent is strictly prohibited and constitutes federal copyright infringement, opening liability to statutory damages, legal fees, and injunctions.
          </p>
        </section>
        {/* Developer Attribution & Portfolio */}
        <section className="border-t border-[var(--border)] pt-8">
          <h2 className="text-xl font-display font-bold text-[var(--brand-primary)]">
            Developer &amp; Platform Engineering
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            REX Deep Research Pipeline is designed, developed, and maintained by Tejas Waroop Akkala. For technical collaborations, portfolio reviews, or engineering details, please{' '}
            <a
              href="https://akkalatejaswaroop.netlify.app"
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-[var(--brand-primary)] hover:opacity-80 transition-opacity font-bold"
            >
              click here
            </a>.
          </p>
        </section>
        <section className="text-center pt-4">
          <a
            href="/"
            className="inline-block rounded-xl bg-[var(--brand-primary)] px-6 py-3 text-sm font-bold text-[var(--background)] transition-all duration-200 hover:scale-105"
          >
            Return to Home
          </a>
        </section>
      </motion.article>
    </section>
  );
}
