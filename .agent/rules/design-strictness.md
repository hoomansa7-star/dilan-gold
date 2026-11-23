# Design Strictness & Anti-AI-Look Rules (قوانین سخت‌گیرانه طراحی رابط کاربری دیلان)

Whenever generating, refactoring, or modifying any frontend UI, HTML, CSS, React, or JavaScript component for Dilan Gold ERP, strictly follow these negative constraints and token rules:

---

## 1. Strictly Prohibited (Negative Constraints - خط قرمزهای طراحی هوش مصنوعی)

1. **NO Generic AI Gradients:**
   - Strictly forbid default purple-to-indigo, cyan-to-violet, or cyber-neon gradients on dark backgrounds.
   - Backgrounds must use intentional, architected surfaces: deep obsidian slate (`#0B0F17`), crisp zinc cards (`#151C28`), or clean off-white canvases (`#F8FAFC`).
2. **NO Cookie-Cutter 3-Column Bento Cards:**
   - Never slap 3 or 4 identical rounded boxes on screen with a centered generic Lucide icon and two lines of text.
   - Use asymmetric grids, clear visual hierarchy, varying column spans (`col-span-2`, `col-span-1`), and information-dense layouts.
3. **NO Arbitrary Magic Numbers:**
   - Never use arbitrary CSS pixel values (e.g., `margin: 13px`, `padding: 17px`, `width: 342px`, `#333`, `#2b2d42`).
   - ALWAYS use strict design tokens:
     - Spacing: 4pt/8pt scale (`4px, 8px, 12px, 16px, 20px, 24px, 32px, 40px, 48px`).
     - Radii: `4px` (sm), `8px` (md), `12px` (lg), `16px` (xl), `9999px` (full pills for status badges only).
     - Colors: Use CSS variables (`var(--bg-page)`, `var(--bg-card)`, `var(--gold-primary)`, `var(--border-color)`).
4. **NO Generic Placeholder SaaS Copy:**
   - Never use vague filler text ("Empower your productivity", "Next-gen platform", "Manage your assets seamlessly").
   - Use authentic, professional Iranian jewelry guild terminology:
     - مظنه روز، آبشده، متفرقه، کار ساخته، بنکدار، کیفی، کارمزد و اجرت، ری‌گیری و انگ، پولی‌کردن، طلایی‌کردن، عیار ۷۵۰ (۱۸)، سوت.
5. **NO Unstyled Raw Divs & Missing States:**
   - Every button, input, and interactive card must have:
     - Hover state (subtle border illumination or background shift).
     - Active/Tactile state (`transform: scale(0.98)` or `active:scale-95`).
     - Focus ring for keyboard accessibility (`focus:ring-2 focus:ring-amber-500/40`).
     - Disabled state with clear visual cue (`opacity-50 cursor-not-allowed`).

---

## 2. Spatial Depth & Luxury Finishing (عمق بصری و فینیشینگ لوکس)

1. **Ultra-Crisp 1px Borders over Muddy Drop Shadows:**
   - Avoid heavy blurred black drop shadows.
   - Use ultra-crisp 1px borders (`border border-slate-200/80` in light mode, `border border-slate-700/60` in dark mode) paired with subtle micro-shadows (`box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 25px -5px rgba(0,0,0,0.05)`).
2. **Glassmorphism & Layered Elevation:**
   - Floating toolbars, sticky headers, and modal backdrops must use `backdrop-blur-xl bg-slate-900/80` or `bg-white/80`.
3. **Financial & Numerical Data Hygiene:**
   - Always use tabular numbers (`font-variant-numeric: tabular-nums; font-feature-settings: 'tnum' 1;`) for monetary values, weights (سوت), percentages, and gold Karat to ensure vertical column alignment.
   - Numbers in Persian guild contexts should be formatted with standard 3-digit comma separators (e.g. `۴۵,۲۵۰,۰۰۰`).

---

## 3. Persian & RTL Bi-directional Rules

1. Root document must always be `<html lang="fa" dir="rtl">`.
2. Use logical CSS utilities (`ms-`, `me-`, `ps-`, `pe-`, `gap-x-`, `start-`, `end-`) instead of hardcoded `left` and `right`.
3. Mirror directional chevrons and arrow icons (next arrow points left, back arrow points right).
4. Primary display font: `Lalezar` / `Estedad Black`.
5. Body and UI font: `Estedad` with proper font weights (`400`, `500`, `600`, `700`, `800`).
