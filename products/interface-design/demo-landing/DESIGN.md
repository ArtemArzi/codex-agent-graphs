---
name: За Край
description: A kinetic expedition poster with a living cloth sculpture
colors:
  ink: "#1c3027"
  hero-ink: "#142c24"
  paper: "#e6e8e1"
  paper-light: "#f1f2eb"
  muted: "#536158"
  line: "#b6bfb2"
  rust: "#b83c23"
  rust-dark: "#96301d"
  focus: "#174e8b"
  map-land: "#d8ddcf"
  water: "#c2ccc7"
  hero-surface: "#c6ccc7"
  selected-route: "#d9dfd2"
  route-hover: "#dce1d6"
  secondary-hover: "#30483c"
  ridge-water: "#c9d1bd"
  ridge-land: "#dce2d3"
  map-contour: "#abb7a6"
  footer-mark: "#3d5043"
  inverted-muted: "#b3bfb0"
  selected-option: "#e2e7db"
  error: "#932e1b"
  metal: "#58635e"
  fallback-fabric: "#df5f2d"
  fabric: "#e95b28"
  fabric-print: "#21362c"
typography:
  kinetic:
    fontFamily: "Unbounded, sans-serif"
    fontSize: "clamp(90px, 12.4vw, 210px)"
    fontWeight: 650
    lineHeight: 1.18
    letterSpacing: "-0.04em"
  display:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "clamp(112px, 13.7vw, 220px)"
    fontWeight: 600
    lineHeight: 1.01
    letterSpacing: "-0.038em"
  body:
    fontFamily: "Golos Text, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Golos Text, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  control: "2px"
spacing:
  page-gutter: "clamp(22px, 4.1vw, 72px)"
  control-inline: "24px"
components:
  button-primary:
    backgroundColor: "{colors.rust}"
    textColor: "{colors.paper-light}"
    rounded: "{rounded.control}"
    height: "55px"
    padding: "0 24px"
  button-primary-hover:
    backgroundColor: "{colors.rust-dark}"
  button-secondary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper-light}"
    rounded: "{rounded.control}"
    height: "55px"
    padding: "0 24px"
---

# Design System: За Край

## Overview

**Creative North Star: "An expedition poster with a usable field guide"**

The mineral landscape, a moving original cloth sculpture and layered Unbounded Cyrillic type carry the identity. The headline sits on two depth planes around a smaller cloth shape. Side rods, the concept badge and the decorative note were removed on user feedback; the cloth now has open space around its edges. The explicit request for an extraordinary first screen authorizes monumental type in this fictional campaign. Supporting information has a clear reading order, useful route
identifiers and calm physical controls. The user delegated this new fictional
concept; it does not replace an existing client's identity.

The six-direction reference gallery is a separate comparison artifact. Its
deliberate variations do not establish six competing worlds on this landing.

## Colors

Cool paper and ink-green form the stable surface. Rust identifies the primary
action and selected-route line, echoing the physical fabric in the original
image. The explicit focus color supports keyboard use. The map's land and water
roles change together for its second illustrative route.

## Typography

The hero uses local OFL Unbounded. Section headings use OFL Oswald; body and controls use Golos Text. These three roles are intentional and local. Large display size belongs to the hero and section hierarchy. Mobile
headings adapt to the available width; route names keep real word separators.
Authored control/metadata text is at least12px; essential explanatory prose is
larger. Fonts and their licenses ship with the demo rather than loading remotely.

## Layout and Spacing

The first screen is a full-height living composition. Its transparent WebGL canvas passes in front of the first headline line and behind the second. A solid information/action plate stays readable independently of the scene. Sections alternate strong type with restrained prose.
The route comparison is a two-row directory beside a schematic map, then stacks
on narrow screens. Fixed section counts and feature-card grids are not required.

## Components

Buttons are nearly square and have visible focus. Related secondary actions
have quieter treatment. Route choices expose selected state in text/semantics
and color. The native dialog owns focus, Escape and a path back to the trigger.
Its save error retains both route and pace. Save/download/confirmation agree.

## Motion

One scene, not a reveal on every section: pinned triangular cloth folds in a procedural wind, a small pointer view shift and a one-time 1050ms letter entrance. The actual planner is ordinary independent HTML/JavaScript. The site is an experience-led campaign with a Persuade action, not a rendered movie.

Three.js 0.186.1 ships locally with MIT notice and exact npm archive integrity. This release publishes unminified module/core builds, which are retained byte-exact. A 48-division mesh has 1225 vertices. There are no side rods. No shadows, postprocessing or physics dependency. The current cloth has no poles or cast shadow. DPR is capped at1.5 desktop/1.2 mobile; drawing is capped at40/30fps. These are resource choices, not a field-performance claim.

The animation loop stops offscreen, in hidden documents, while the planner is open, on manual pause and under reduced motion. Pause causes compose; closing a dialog never overrides manual pause. Reduced motion gives a final still, with the wind range remaining an explicit manual control. Asset, module and WebGL failure retain the static SVG/photo and usable offer/CTA. Context loss disposes owned GPU resources. Page teardown removes owned listeners and observers; BFCache retains pause intent.

## Imagery

The hero is an original generated landscape, not evidence of a real location. The clean plate removes the prior static cloth and person so that the cloth is rendered live in code. Both original images and exact prompts are retained in assets/*image-provenance.json and PNG metadata. The fabric weave and lettering are original Canvas2D art, not a brand asset.
The static map is an original schematic with explicit fictional labeling.

## Rules

Do preserve the relationship between the image, monumental type and useful
annotation. Do keep main actions visible and route information consistent.
Do mark the fictional project and local-save boundary clearly. Do not import
the reference brands' claims, identities, imagery or whole layouts. Do not turn
this expedition palette into the default for every future project.
