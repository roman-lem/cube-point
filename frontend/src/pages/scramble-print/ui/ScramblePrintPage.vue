<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { fetchMeetup, fetchPrintScrambles, type MeetupPageData, type PrintEvent } from '@/entities/meetup'
import { ApiError } from '@/shared/api'
import { formatDate, plural } from '@/shared/lib'
import { AppButton, AppCard, AppIcon, PageHeader } from '@/shared/ui'
import ScrambleBlank from './ScrambleBlank.vue'

// Печать бланков со скрамблами: бланк A5 на участника, по два на листе A4.
// Скрамблы одинаковые у всех, поэтому бланки одинаковые. FMC не печатается —
// его скрамбл выдаётся только после старта попытки.
const { meetupId } = defineProps<{ meetupId: number }>()

const MAX_BLANKS = 200

const page = ref<MeetupPageData | null>(null)
const events = ref<PrintEvent[]>([])
const blanks = ref(2)
const error = ref('')

async function load() {
  try {
    const [data, scrambles] = await Promise.all([
      fetchMeetup(meetupId),
      fetchPrintScrambles(meetupId),
    ])
    page.value = data
    events.value = scrambles
    // По бланку на подтверждённого участника, с запасом до чётного — лист A4 целиком.
    const count = Math.max(data.meetup.participants_count, 2)
    blanks.value = count + (count % 2)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить скрамблы'
  }
}

watch(() => meetupId, load, { immediate: true })

const safeBlanks = computed(() =>
  Math.min(Math.max(Math.floor(Number(blanks.value)) || 1, 1), MAX_BLANKS),
)
/** Листы A4 по два бланка. */
const sheets = computed(() =>
  Array.from({ length: Math.ceil(safeBlanks.value / 2) }, (_, i) =>
    Math.min(2, safeBlanks.value - i * 2),
  ),
)

const title = computed(() => page.value?.meetup.club.name ?? '')
const subtitle = computed(() => {
  const meetup = page.value?.meetup
  if (!meetup) {
    return ''
  }
  return [`Встреча ${formatDate(meetup.date)}`, meetup.place].filter(Boolean).join(' · ')
})
const hasFmc = computed(() => page.value?.meetup.events.some((e) => e.event_id === '333fm'))

function print() {
  window.print()
}
</script>

<template>
  <main class="scramble-print">
    <div class="page scramble-print__toolbar">
      <PageHeader
        title="Бланки со скрамблами"
        :subtitle="subtitle"
        :back-to="{ name: 'meetup-manage', params: { meetupId } }"
      />
      <AppCard v-if="error">{{ error }}</AppCard>
      <AppCard v-else-if="page && page.my_role !== 'organizer'">
        Печать бланков доступна только организатору клуба
      </AppCard>
      <AppCard v-else-if="page" class="scramble-print__controls">
        <label class="scramble-print__count">
          <span>Число бланков</span>
          <input v-model.number="blanks" type="number" min="1" :max="MAX_BLANKS" inputmode="numeric" />
        </label>
        <p class="page__muted">
          {{ plural(sheets.length, ['лист', 'листа', 'листов']) }} A4, альбомная ориентация,
          по два бланка A5 — разрежьте лист пополам.
          <template v-if="hasFmc">FMC на бланках нет: его скрамбл выдаётся после старта попытки.</template>
        </p>
        <AppButton :disabled="events.length === 0" @click="print">
          <AppIcon name="print" :size="20" />
          Печать
        </AppButton>
        <p v-if="events.length === 0" class="page__muted">На встрече нет дисциплин для бланков.</p>
      </AppCard>
    </div>

    <div v-if="page && events.length" class="scramble-print__sheets">
      <div v-for="(count, index) in sheets" :key="index" class="scramble-print__sheet">
        <ScrambleBlank
          v-for="n in count"
          :key="n"
          :title="title"
          :subtitle="subtitle"
          :events="events"
        />
      </div>
    </div>
  </main>
</template>

<style scoped>
.scramble-print__controls {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.scramble-print__count {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-weight: var(--font-weight-label);
}

.scramble-print__count input {
  width: 96px;
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  font-family: var(--font-mono);
}

/* Превью на экране: листы A4 в альбомной ориентации, с прокруткой на узком экране. */
.scramble-print__sheets {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-5);
  padding: 0 var(--page-padding) var(--space-6);
  overflow-x: auto;
}

.scramble-print__sheet {
  display: flex;
  flex-shrink: 0;
  width: 297mm;
  height: 210mm;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

/* Линия разреза между бланками. */
.scramble-print__sheet > :first-child:not(:last-child) {
  border-right: 0.2mm dashed var(--color-text-secondary);
}

@media print {
  .scramble-print__toolbar {
    display: none;
  }

  .scramble-print__sheets {
    display: block;
    padding: 0;
    overflow: visible;
  }

  .scramble-print__sheet {
    border: none;
    break-after: page;
  }

  .scramble-print__sheet:last-child {
    break-after: auto;
  }
}
</style>

<style>
/* Лист печати: A4 альбомный без полей — отступы задаёт сам бланк. */
@page {
  size: A4 landscape;
  margin: 0;
}

@media print {
  body {
    background: var(--color-surface);
  }
}
</style>
