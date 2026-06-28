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

---

## 4. Visual Asset Pipeline (VSF Manifest)

To elevate the repository branding and make the project stand out visually to judges, we utilize DALL-E 3 or Midjourney to generate bespoke visual assets. Below is the active asset manifest and the prompts used to create them.

### Asset Manifest

| Asset # | Name | Type | Target Path | Status |
|:---:|---|---|---|---|
| **1** | Master Repository Banner | Hero Cover (21:9) | `docs/assets/hero_banner.webp` | ⏳ Pending Generation |
| **2** | Project Logo | Square Icon (1:1) | `docs/assets/logo.png` | ⏳ Pending Generation |
| **3** | The Guard Gate | 3D Concept (16:9) | `docs/assets/guard_gate.webp` | ⏳ Pending Generation |
| **4** | Topographic Texture | Background Pattern (16:9) | `docs/assets/topo_bg.webp` | ⏳ Pending Generation |

### Copy-Paste Generation Prompts (DALL-E 3 / Midjourney)

#### 1. Master Repository Banner (Hero Cover)
> A photorealistic cinematic wide banner of a high-tech talent forensics operations room. A sleek midnight-black obsidian glass table sits in the center, reflecting glowing electric teal and champagne gold holographic data lines. Above the surface, three circular, floating, translucent lens elements (representing 'Three Eyes') are hovering in vertical alignment. The lens elements project crisp volumetric laser lines scanning a cloud of floating candidate nodes. Volumetric dark digital fog and microscopic dust particles drift through clean gold god rays. Shot on RED V-RAPTOR with a wide anamorphic lens. Cinematic film grain, shallow depth of field. The scene feels precise, mysterious, and high-fidelity. No text, no logos, no watermarks, no human figures. Aspect ratio 21:9.

#### 2. Project Logo (Brand Mark)
> A minimalist, geometric logo mark on a pure black background. The mark consists of three interlocking, concentric geometric circles forming a stylized three-eyed lens aperture. The outer circle glows in luminous electric teal (#00E5CC), the middle circle in muted champagne gold (#D4AF37), and the inner focal core is a bright, white light source. Highly refined vector aesthetic with subtle metallic beveling and three-dimensional glass depth. The design is iconic, clean, and futuristic—like a logo for an elite cybersecurity or talent intelligence platform. Perfectly centered. No text, no labels, 1:1 aspect ratio.

#### 3. The Guard Gate (Stage 1 Filtering)
> A conceptual 3D render of a futuristic digital gateway. On the left side, chaotic, corrupted crimson cubes and red floating code anomalies are magnetically pulled into a glowing red quarantine laser grid. On the right side, pristine, glowing emerald green geometric nodes pass through a clean teal archway. The floor is dark polished concrete with sharp light reflections. Volumetric lighting and soft shadow mapping. The scene represents security, filtering, and trust verification. Atmospheric digital background. No text, no watermarks, 16:9 aspect ratio.

#### 4. Topographic Texture (Background Pattern)
> A seamless, ultra-dark abstract background texture. Perceptible, thin topographic contour lines glowing faintly in electric teal (#00E5CC) and dark gray against a near-black obsidian background (#08090E). The lines wave across the canvas organically, like a fingerprint or digital map. No bright spots, low contrast, subtle noise grain. Designed as a professional background pattern for premium web UI. 16:9 aspect ratio, no text.
