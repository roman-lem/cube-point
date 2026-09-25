<script setup lang="ts">
import { computed } from 'vue'
import type { PrintEvent } from '@/entities/meetup'
import { FORMAT_NAMES, eventName } from '@/shared/lib'

// Бланк участника формата A5: все скрамблы встречи (кроме FMC) и поля под попытки.
// Раскладка пока фиксированная. Если понадобится разметка бланка (логотип, свои блоки,
// расположение скрамблов), её удобно передавать сюда отдельным объектом-макетом.
const { title, subtitle, events } = defineProps<{
  title: string
  subtitle: string
  events: PrintEvent[]
}>()

// Чем больше строк, тем они ниже, чтобы все дисциплины влезли на A5.
const rowHeight = computed(() => {
  const rows = events.reduce((sum, e) => sum + e.scrambles.length, 0)
  return rows <= 15 ? '8mm' : rows <= 20 ? '6.8mm' : '5.6mm'
})
</script>

<template>
  <article class="scramble-blank" :style="{ '--row-height': rowHeight }">
    <header class="scramble-blank__header">
      <div>
        <p class="scramble-blank__title">{{ title }}</p>
        <p class="scramble-blank__subtitle">{{ subtitle }}</p>
      </div>
      <p class="scramble-blank__name">Имя и фамилия</p>
    </header>

    <section v-for="event in events" :key="event.event_id" class="scramble-blank__event">
      <p class="scramble-blank__event-title">
        {{ eventName(event.event_id) }}
        <span>· {{ FORMAT_NAMES[event.format] }}</span>
      </p>
      <ol class="scramble-blank__rows">
        <li v-for="(scramble, index) in event.scrambles" :key="index" class="scramble-blank__row">
          <span class="scramble-blank__number">{{ index + 1 }}</span>
          <span class="scramble-blank__scramble">{{ scramble }}</span>
          <span class="scramble-blank__field" />
        </li>
      </ol>
    </section>
  </article>
</template>

<style scoped>
/* Бланк печатается чёрным по белому: берём самый тёмный и самый светлый токены. */
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

.scramble-blank__field {
  flex: 0 0 22mm;
  height: calc(var(--row-height) - 1.2mm);
  border: 0.2mm solid var(--color-text-primary);
}
</style>
