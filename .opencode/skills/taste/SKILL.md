---
name: taste
description: Design taste principles for evaluating and refining visual UI. Use when making aesthetic decisions, reducing visual clutter, or improving typography/spacing.
---

# Taste — Visual Design Principles

When making design decisions, apply these taste principles in order:

## 1. Remove, Don't Add
Before adding any new element (border, shadow, background, icon), ask: can I remove something instead? Great design subtracts to reveal essence.
- If information is clear without a border → remove the border
- If hierarchy is obvious without a background → remove the background
- If meaning is carried by position → remove the label

## 2. Typography First
Type is the backbone of UI. Get it right before anything else.
- Use **one** typeface family; two at most
- Size contrast: headings should be noticeably larger (1.5-2.5x body size)
- Weight contrast: bold for emphasis, regular for body — nothing in between
- Line-height: 1.5-1.6 for body text, 1.1-1.3 for headings
- Letter-spacing: -0.01em to 0 for body, 0.05-0.2em for uppercase labels
- Color: one primary text color, one muted/secondary, one disabled — no more

## 3. Borders Are Last Resort
Borders add visual noise. Prefer:
1. **Whitespace** — gaps between elements signal separation
2. **Background contrast** — slightly different surface colors
3. **Shadow** — elevation replaces outlines
4. **Border** — only when nothing else works, and then use the faintest possible

## 4. Shadows With Purpose
Shadows should be felt, not seen:
- Use small blur (4-8px) for subtle elevation
- Shadow color should be the background color darkened, not pure black
- Never use more than 3 elevation levels
- Inner shadows for inset/active states

## 5. Color Restraint
- One dominant background color
- One primary accent (used sparingly, only for the most important action)
- One secondary/muted accent for interactive states
- Gray scale for everything else
- Never use pure black (`#000`) or pure white (`#fff`) — always tint

## 6. Spacing Rhythm
- Use a single base unit (e.g., 4px or 8px)
- All padding/margin/gap must be multiples of this unit
- Larger spaces = more important separations
- Elements that belong together should be closer than elements that don't

## 7. Interaction States
Every interactive element needs:
- **Default** — clean, minimal
- **Hover** — subtle brightness/saturation shift (~10%), or very subtle border glow
- **Active/Pressed** — slightly darker or inset
- **Focused** — visible ring (for keyboard nav)
- **Disabled** — reduced opacity (0.3-0.5)

## 8. Motion as Information
- Duration: 150-250ms for micro-interactions, 300-500ms for transitions
- Easing: ease-out for entering elements, ease-in for exiting
- Only animate transform and opacity (GPU-composited)
- One animation at a time; never simultaneous competing motions

## Quality Checklist
Before finalizing any UI:
- [ ] Can I remove any borders, backgrounds, or labels?
- [ ] Is the typography hierarchy immediately clear?
- [ ] Are spacing values consistent (all multiples of base unit)?
- [ ] Is there exactly one accent color, used sparingly?
- [ ] Do shadows feel natural (not harsh)?
- [ ] Does every hover/active/disabled state exist?
- [ ] Are animations under 300ms and only on transform/opacity?
