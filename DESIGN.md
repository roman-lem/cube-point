---
name: Speedcubing Club App
colors:
  background: "#F7F8FA"
  surface: "#FFFFFF"
  text-primary: "#1A1D23"
  text-secondary: "#6B7280"
  border: "#E5E7EB"
  primary: "#2563EB"
  on-primary: "#FFFFFF"
  personal-best: "#16A34A"
  club-record: "#7C3AED"
  dnf: "#DC2626"
typography:
  body:
    fontFamily: "Manrope"
    fontSize: 16
    fontWeight: 400
  label:
    fontFamily: "Manrope"
    fontSize: 14
    fontWeight: 600
  heading:
    fontFamily: "Manrope"
    fontSize: 22
    fontWeight: 700
  time-large:
    fontFamily: "JetBrains Mono"
    fontSize: 20
    fontWeight: 600
  time-small:
    fontFamily: "JetBrains Mono"
    fontSize: 14
    fontWeight: 400
rounded:
  card: 12
  button: 8
  badge: 6
spacing:
  scale: [4, 8, 12, 16, 24, 32]
---

# Design System: Speedcubing Club App

## Overview
A web app for local speedcubing communities: meetups, mini-competitions, club records and personal statistics. The mood is calm and sporty: lots of whitespace, no decorative elements, numbers are the hero of every screen. The interface is mobile-first but every screen must also work well on desktop (organizers often manage meetups from a laptop). UI language is Russian.

## Colors
- **Background** (#F7F8FA) for the page, **Surface** (#FFFFFF) for cards and lists.
- **Primary** (#2563EB) is the single accent: main buttons, links, active states, the "live" indicator. Do not introduce other accent colors.
- Status colors are reserved for result semantics only, never for decoration:
  - **Personal best** (#16A34A) — "PB" badge.
  - **Club record** (#7C3AED) — "LR" badge (local record of this club).
  - **DNF** (#DC2626) — failed attempts and DNF averages.

## Typography
- Manrope for all interface text (supports Cyrillic).
- JetBrains Mono with tabular numerals for every time, average and move count, so columns do not shift when results update live.
- Times are the largest and boldest element in a result row; names are secondary in visual weight.

## Layout
- Mobile: single column, 16px side padding, full-width cards.
- Desktop: content centered with a max width around 960px; organizer screens may use a two-column layout (list + details). Do not simply stretch mobile layouts to full width.
- Generous vertical spacing between groups; tight spacing inside a result row.

## Shapes
Cards 12px radius, buttons and inputs 8px, badges 6px. Flat design: no shadows or only a very subtle one on cards; separate elements with whitespace and thin borders (#E5E7EB).

## Components
Every screen is built from the named components below. When a screen needs one of these elements, reuse the component exactly as described here, with the same anatomy, sizes and colors on every screen. Do not invent variations of them.

### Base
- **AppButton:** variants primary (filled #2563EB, white text), secondary (outlined), danger (#DC2626 text or outline; never a filled red button next to normal actions). Height 44px, radius 8px.
- **AppInput:** white background, 1px #E5E7EB border, radius 8px, label above the field, error text in #DC2626 below.
- **AppCard:** white surface, radius 12px, 16px padding, thin border, no or very subtle shadow.
- **PageHeader:** back arrow, title, optional subtitle line in secondary text, optional action on the right.
- **BottomNav** (mobile only, becomes a top bar on desktop): 4 items with icon and label.

### Results
- **TimeValue:** a single time, average or move count in JetBrains Mono with tabular numerals. States: normal, "+2" suffix, DNF (red text), empty "—". Sizes: large (averages) and small (attempts, singles).
- **RecordBadge:** small pill, white text on the status color. Variants: "PB" (#16A34A), "LR" (#7C3AED). No other badge variants.
- **AttemptSeries:** a horizontal row of all attempts of one series (5 cells for ao5, 3 for mo3/bo3, 1 for bo1), each cell a small TimeValue in a light rounded box. Attempts that do not count toward the average are wrapped in parentheses. Unfinished attempts are empty cells. This exact component is used everywhere a series is shown: expanded ResultRow, participant profile, meetup history, organizer result editing.
- **ResultRow:** place number in a circle, participant name, best single (small TimeValue), RecordBadge(s), average (large TimeValue) on the right, chevron. Collapsed and expanded states; expanded shows AttemptSeries below. States: default, current user (light primary background and left accent bar), unfinished (shows "N из 5 попыток" and "—"), DNF.
- **LiveIndicator:** small pulsing primary dot with the word "LIVE".

### Meetups and clubs
- **EventCard:** event name (3x3, 2x2, OH, FMC, 3BLD...), format (ao5 / mo3 / bo3 / bo1), number of participants, current user's result if any. Used on meetup pages.
- **MeetupCard:** date, place, list of events, participant count, LiveIndicator if the meetup is ongoing.
- **ScrambleBlock:** attempt number and the scramble in JetBrains Mono on a light background. Used only on solving screens, never on results pages.

## Domain rules
- Meetups have no rounds, finals or stages: each participant submits exactly one series per event during the meetup. Never show "Раунд" or "Финал".
- Scrambles are generated by the app, not official WCA scrambles. Never label them as official.
- Result formats: average of 5 (ao5), mean of 3 (mo3), best of 3 (bo3), best of 1 (bo1). FMC results are move counts, not times.
- Times are shown as seconds with two decimals (9.87, 1:02.45 above one minute). Penalties: "+2" is shown next to the time; DNF replaces the time.
- An unfinished series shows its entered attempts and "—" instead of the average.

## Do's and Don'ts
- Do keep numbers dominant and perfectly aligned.
- Do use realistic speedcubing data in mockups (Russian names, times between 8 and 40 seconds).
- Don't use the status colors outside of results.
- Don't use the abbreviations CR, NR or WR for club records: those are official WCA records. Use "LR".
