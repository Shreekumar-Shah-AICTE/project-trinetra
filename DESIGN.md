# 🎨 Project Trinetra (त्रिनेत्र) — UI/UX Design System (VSF)

> **Visual Supremacy Framework (VSF) Guidelines**
> *We do not build interfaces. We build forensic experiences.*

---

## 1. Brand Identity & Visual Vibe

Project Trinetra is a **talent forensics engine**. The visual design must feel like a **military-grade intelligence dashboard** mixed with a sleek **financial operations console**. It is designed to look premium, modern, and trustworthy.

*   **Visual Mood**: Controlled Power, Forensic Accuracy, Luminous Clarity.
*   **Theme**: Dark Mode by default.
*   **Colors**:
    *   **Primary Background**: Deep Obsidian (`#08090E` to `#0B0C10` gradient)
    *   **Secondary Surface/Cards**: Translucent dark slate with glassmorphic borders (`rgba(255,255,255,0.04)`) and backdrop blur.
    *   **Text Colors**: Silver/light gray (`#C5C6C7`) for body text; White (`#FFFFFF`) for headers.
    *   **Accent Color (Teal)**: Luminous Electric Teal (`#00E5CC`) representing verified trust and precision.
    *   **Highlight Color (Gold)**: Muted Champagne Gold (`#D4AF37`) representing premium shortlists.
*   **Typography**:
    *   **Headers**: "Space Grotesk" (Google Fonts) — geometric, technical, high-precision.
    *   **Body**: "Plus Jakarta Sans" or "Inter" — clean, highly legible at small sizes.

---

## 2. Trust Grade Badges (Visual Signaling)

Trust grades represent the core paradigm of "Trust Before Relevance". They must stand out with clear, glowing colors:

| Trust Grade | Meaning | Badge Color | Hex Code | Visual Style |
|:---:|---|:---:|:---:|---|
| **A** | Impeccable profile integrity | Emerald Glow | `#10B981` | Green pill, background glow |
| **B** | Solid profile, minor discrepancies | Mint | `#34D399` | Light green pill |
| **C** | Noticeable gaps or service-heavy | Amber | `#F59E0B` | Yellow pill |
| **D** | High risk / suspicious patterns | Orange | `#F97316` | Orange pill |
| **F** | Hard honeypot / fabricated | Crimson Pulse| `#EF4444` | Red pill with pulsing animation |

---

## 3. UI/UX Signature Components

### 1. The Multi-Stage Interactive Funnel
Instead of jumping straight to a table of candidates, the dashboard shows the candidates moving through the stages of the pipeline:
*   **Beat 1 (Load)**: Visual file uploader or sample selector.
*   **Beat 2 (Quarantine)**: Red banner of honeypots caught + reasons, and a counts of disqualified/filtered entries.
*   **Beat 3 (RRF Fusion)**: The survivors ranked and plotted.

### 2. The Talent Forensics Case File (Candidate Detail)
When expanding a candidate, the UI renders a detailed report block:
*   **Grade Status Box**: Clean left-border colored by Trust Grade, detailing the Guard Gate's findings (chronological checks, stuffer checks, etc.).
*   **Radar/Bar Graph of Dimensions**: Visually maps out their independent ranks:
    *   *Skill Relevance*
    *   *Career Trajectory*
    *   *Behavioral Availability*
    *   *Trust Score*
    *   *Semantic Fit*
*   **Interactive Career Timeline**: A vertical list of past jobs with colored tags indicating company type (Product, Services, Fictional).
*   **Behavioral Signals Dashboard**: KPIs like Response Time (hours), Notice Period (days), Activity Recency, and GitHub Score.
