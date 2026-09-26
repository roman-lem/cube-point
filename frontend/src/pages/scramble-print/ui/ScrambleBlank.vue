<script setup lang="ts">
import type { PrintEvent } from '@/entities/meetup'
import { FORMAT_NAMES, eventName, scrambleLines } from '@/shared/lib'
import { LONG_SCRAMBLE } from '../model/layout'

// A page of an A5 participant score sheet: meetup scrambles (except FMC) and fields
// for attempts. A long sheet has several pages, the split is in model/layout.ts.
// The layout is fixed for now. If a sheet layout is needed (logo, custom blocks,
// scramble placement), it is convenient to pass it here as a separate layout object.
const { title, subtitle, events, rowHeight, page = 1, pages = 1 } = defineProps<{
  title: string
  subtitle: string
  events: PrintEvent[]
  /** Minimum row height, mm. */
  rowHeight: number
  page?: number
  pages?: number
}>()
</script>

<template>
  <article class="scramble-blank" :style="{ '--row-height': `${rowHeight}mm` }">
    <header class="scramble-blank__header">
      <div>
        <p class="scramble-blank__title">{{ title }}</p>
        <p class="scramble-blank__subtitle">
          {{ subtitle }}<template v-if="pages > 1"> · лист {{ page }} из {{ pages }}</template>
        </p>
      </div>
      <p class="scramble-blank__name">Имя</p>
    </header>

    <section v-for="event in events" :key="event.event_id" class="scramble-blank__event">
      <p class="scramble-blank__event-title">
        {{ eventName(event.event_id) }}
        <span>· {{ FORMAT_NAMES[event.format] }}</span>
      </p>
      <ol class="scramble-blank__rows">
        <li v-for="(scramble, index) in event.scrambles" :key="index" class="scramble-blank__row">
          <span class="scramble-blank__number">{{ index + 1 }}</span>
          <span
            :class="[
              'scramble-blank__scramble',
              { 'scramble-blank__scramble--small': scramble.length > LONG_SCRAMBLE },
            ]"
          >
            <span v-for="(line, n) in scrambleLines(event.event_id, scramble)" :key="n" class="scramble-blank__line">
              {{ line }}
            </span>
          </span>
          <span class="scramble-blank__field" />
        </li>
      </ol>
    </section>
  </article>
</template>

<style scoped>
/* The sheet is printed black on white: take the darkest and the lightest tokens. */
.scramble-blank {
  display: flex;
  flex-direction: column;
  gap: 2.5mm;
  width: 148.5mm;
  height: 210mm;
  padding: 8mm;
  overflow: hidden;
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 9pt;
  line-height: 1.2;
}

.scramble-blank__header {
  display: flex;
  justify-content: space-between;
  gap: 4mm;
  padding-bottom: 2mm;
  border-bottom: 0.4mm solid var(--color-text-primary);
}

.scramble-blank__title {
  font-size: 11pt;
  font-weight: 700;
}

.scramble-blank__name {
  flex: 0 0 60mm;
  align-self: flex-end;
  padding-top: 6mm;
  border-top: 0.2mm solid var(--color-text-primary);
  font-size: 7pt;
}

.scramble-blank__event-title {
  margin-bottom: 1mm;
  font-weight: 700;
}

.scramble-blank__event-title span {
  font-weight: 400;
}

.scramble-blank__rows {
  margin: 0;
  padding: 0;
  list-style: none;
}

.scramble-blank__row {
  display: flex;
  align-items: center;
  padding: 0.7mm 0;
  gap: 2mm;
  min-height: var(--row-height);
  border-bottom: 0.2mm solid var(--color-border);
}

.scramble-blank__number {
  flex: 0 0 4mm;
  font-weight: 700;
}

.scramble-blank__scramble {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 7.5pt;
  overflow-wrap: anywhere;
}

.scramble-blank__scramble--small {
  font-size: 6.5pt;
}

.scramble-blank__line {
  display: block;
}

.scramble-blank__field {
  flex: 0 0 22mm;
  height: calc(var(--row-height) - 1.2mm);
  border: 0.2mm solid var(--color-text-primary);
}
</style>
