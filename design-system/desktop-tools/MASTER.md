# Desktop Tools UI Design System (ui-ux-pro-max)

> Generated with `ui-ux-pro-max` workflow, then curated using domain results:
> - `style`: Flat Design
> - `color`: SaaS productivity light palettes
> - `typography`: Developer Mono (JetBrains Mono + IBM Plex Sans)
> - `ux`: focus states, hover states, compact spacing, form clarity

---

## A. Product Intent

- Product type: desktop developer utility app
- UX goal: fast scanning + low cognitive load
- Visual direction: **compact, bright, clean, flat, modern**
- Must avoid: over-decorative effects, thick border-heavy look, marketing-style whitespace

---

## B. Chosen Style Contract

### Primary Style: Flat Design (from skill)

- 2D, minimalist, clean geometry
- no heavy shadows, no glass blur, no gradient-heavy panels
- subtle hover via color/opacity shift
- transition window: `150-200ms`
- optimized for dashboards / tools / SaaS workflows

### Why This Style

- Matches dense productivity scenarios better than glassmorphism.
- Improves readability and perceived speed.
- Easier consistency across many modules.

---

## C. Color System

### Core Palette

| Token | Value | Usage |
|------|------|------|
| `color.bg.canvas` | `#F8FAFC` | Global page background |
| `color.bg.surface` | `#FFFFFF` | Cards, sidebars, toolbars |
| `color.bg.subtle` | `#F1F5F9` | Alternate rows, neutral chips |
| `color.bg.hover` | `#E2E8F0` | Hover feedback |
| `color.text.primary` | `#1E293B` | Main labels/content |
| `color.text.secondary` | `#475569` | Secondary text |
| `color.text.tertiary` | `#94A3B8` | Placeholder/meta |
| `color.accent.primary` | `#3B82F6` | Primary action |
| `color.accent.active` | `#2563EB` | Pressed/active state |
| `color.accent.soft` | `#DBEAFE` | Selected tab/nav background |

### Semantic Colors

| Token | Value |
|------|------|
| `color.success` | `#16A34A` |
| `color.warning` | `#D97706` |
| `color.error` | `#DC2626` |
| `color.info` | `#0EA5E9` |

### Color Rules

- Accent only for key interactive anchors.
- Use tonal separation (canvas/surface/subtle) before adding borders.
- Default text should never be lighter than `#475569` in light mode.

### Tailwind Reference Mapping

| Design Token | Tailwind-style Class | Hex |
|------|------|------|
| `color.bg.canvas` | `bg-slate-50` | `#F8FAFC` |
| `color.bg.surface` | `bg-white` | `#FFFFFF` |
| `color.bg.subtle` | `bg-slate-100` | `#F1F5F9` |
| `color.bg.hover` | `bg-slate-200` | `#E2E8F0` |
| `color.text.primary` | `text-slate-900` | `#1E293B` |
| `color.text.secondary` | `text-slate-600` | `#475569` |
| `color.text.tertiary` | `text-slate-400` | `#94A3B8` |
| `color.accent.primary` | `bg-blue-500` | `#3B82F6` |
| `color.accent.active` | `bg-blue-600` | `#2563EB` |
| `color.accent.soft` | `bg-blue-100` | `#DBEAFE` |
| `color.success` | `text-green-600` | `#16A34A` |
| `color.warning` | `text-amber-600` | `#D97706` |
| `color.error` | `text-red-600` | `#DC2626` |

Use these class names as naming inspiration in docs/reviews even though implementation is QML.

### Project Tailwind Preset Contract

This project uses a **Tailwind-style design preset** as the single source of truth, implemented in `src/app/theme/Theme.js`.

- `palette`: Tailwind-like color scales (`slate`, `blue`, `green`, `amber`, `red`, `cyan`)
- `light` / `dark`: semantic tokens mapped from palette
- `twLight` / `twDark`: utility class style aliases (`bg-slate-50`, `text-slate-600`, etc.)
- `spacing`: Tailwind-like spacing scale (`s1..s5`)
- `radius`: Tailwind-like rounded scale (`sm..xl`)
- `typeScale`: typography scale for title/heading/body/caption

Rule: add new design values to this preset first, then consume in QML components/pages.  
Do not hardcode page-level colors, spacing, or radius.

---

## D. Typography System

### Font Pairing (from typography domain result)

- UI text: `IBM Plex Sans`
- Code/data/method/status: `JetBrains Mono`

### Type Scale

| Role | Size | Weight | Font |
|------|------|------|------|
| Page title | `20-22` | 600 | IBM Plex Sans |
| Section title | `14-16` | 600 | IBM Plex Sans |
| Body/control | `12-13` | 400/500 | IBM Plex Sans |
| Dense meta row | `10-11` | 400/500 | JetBrains Mono |

### Readability Rules

- Keep line-height compact but readable (`1.35-1.45`).
- Avoid all-caps for long labels.
- Use mono only where data alignment helps comprehension.

---

## E. Spacing, Density, Radius

### Spacing Tokens

| Token | Value |
|------|------|
| `space.1` | `4` |
| `space.2` | `8` |
| `space.3` | `10` |
| `space.4` | `12` |
| `space.5` | `16` |

### Tailwind Spacing Reference

| Token | Value | Tailwind-style |
|------|------|------|
| `space.1` | `4` | `p-1`, `m-1` |
| `space.2` | `8` | `p-2`, `m-2`, `gap-2` |
| `space.3` | `10` | between `2` and `3` (custom) |
| `space.4` | `12` | `p-3`, `m-3`, `gap-3` |
| `space.5` | `16` | `p-4`, `m-4`, `gap-4` |

### Density Targets

- Button/input height: `34-36`
- Toolbar strip: `44-48`
- Dense list row: `32-36`
- Standard row: `38-40`
- Container padding: mostly `8-12`

### Radius Targets

- Small controls/rows: `6`
- Inputs/buttons/chips: `8`
- Main cards/panels: `10`

### Tailwind Radius Reference

| Token | Value | Tailwind-style |
|------|------|------|
| `radius.sm` | `6` | `rounded-md` (close) |
| `radius.md` | `8` | `rounded-lg` |
| `radius.lg` | `10` | custom between `rounded-lg` and `rounded-xl` |
| `radius.xl` | `12` | `rounded-xl` |

---

## F. Border And Surface Policy (Critical)

### Border Minimization Rule

- Use border only when it adds function:
  - input boundary
  - focus boundary
  - data table separation where needed
- Avoid framing every panel with a strong border.

### Preferred Hierarchy

1. Background tone separation (`canvas` vs `surface` vs `subtle`)
2. Spacing + alignment
3. Optional subtle border
4. Never start with heavy outlines

---

## G. Interaction Specification (from ux domain)

### Required States

- Hover: visible but subtle background shift
- Pressed: one-step darker fill
- Focus: clear visible ring/border (`2px` equivalent)
- Disabled: muted fill + muted text + non-interactive cursor

### Timing

- Transitions: `150-200ms`
- No scale-based hover on dense tool controls
- No flashy motion in data panels

### Accessibility Rules

- Preserve visible keyboard focus state at all times
- Maintain 4.5:1 contrast minimum for text
- Keep adjacent interactive spacing at least `8px`

---

## H. QML Component Contract

### `UiButton`

- Variants: `primary`, `secondary`, `ghost`
- Flat fills; default no border for primary/secondary
- Primary:
  - idle `#3B82F6`
  - hover `#60A5FA` or close tone
  - pressed `#2563EB`
- Secondary:
  - tonal neutral fill (`#EEF2F7` -> `#E2E8F0` on hover)

### `UiTextField` / `UiTextArea`

- Light surface background
- subtle default border (`#CBD5E1`/`#94A3B8`)
- focus color `#3B82F6`
- no shadows, no glass effects

### `UiTabButton`

- Active uses soft accent fill (`#DBEAFE`) + accent text
- Inactive uses transparent/subtle hover fill
- Avoid outlined boxes for every tab

---

## I. Page-Level Rules

### Main Shell

- Bright base background and flat containers
- Navigation active state via soft fill chip, not boxed border
- Keep top bar thin and utilitarian

### API Test Workbench

- Two-pane compact layout
- Dense rows with predictable rhythm
- Inputs/tabs/response areas share same flat tokens
- status colors only on status text, not on full rows

### Other Modules

- Must reuse shared primitives
- No module-specific visual drift

---

## J. Anti-Patterns

- Glassmorphism panels on core workflow pages
- Thick border outlines on every container
- Decorative gradients as main UI identity
- Large empty whitespace harming efficiency
- Mixing native default controls with custom components

---

## K. QA Checklist (Implementation Gate)

- [ ] Light theme baseline is visually complete
- [ ] Flat look achieved without heavy borders
- [ ] Compact density preserved with readable text
- [ ] Hover/focus/pressed/disabled implemented on all interactive controls
- [ ] Focus visibility verified via keyboard navigation
- [ ] Accent color usage limited to actionable/high-priority elements
- [ ] Visual consistency maintained across all modules
