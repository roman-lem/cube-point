<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { Meetup, MeetupSummary } from '@/entities/meetup'
import {
  EVENT_IDS, EVENTS, FORMAT_NAMES, FORMATS, formatTime, todayIn, useFormErrors,
  type EventId, type SeriesFormat,
} from '@/shared/lib'
import { AppButton, AppCard, AppInput, AppSelect, FormError } from '@/shared/ui'
import { createMeetup } from '../api/createMeetup'
import { generateScrambles } from '../lib/scrambles'

const { clubId, timezone, previous } = defineProps<{
  clubId: number
  timezone: string
  /** The club's latest meetup: time, place and address are taken from it. */
  previous: MeetupSummary | null
}>()
const emit = defineEmits<{ created: [meetup: Meetup] }>()

const { fieldErrors, formError, clearErrors, showError } = useFormErrors()

// Today by the club's clock; the rest is as at the club's latest meetup, empty for the first one.
const form = reactive({
  date: todayIn(timezone),
  starts_at: previous ? formatTime(previous.starts_at, timezone) : '',
  ends_at: previous?.ends_at ? formatTime(previous.ends_at, timezone) : '',
  place: previous?.place ?? '',
  address: previous?.address ?? '',
})

// Events selected by default: the most common at club meetups.
const DEFAULT_SELECTED: EventId[] = ['333', '222', '333oh', 'pyram']

// All events as a list; the selected ones go into the meetup in the same order.
const events = reactive(
  EVENT_IDS.map((eventId) => ({
    eventId,
    selected: DEFAULT_SELECTED.includes(eventId),
    format: EVENTS[eventId].defaultFormat as SeriesFormat,
  })),
)

const formatOptions = FORMATS.map((value) => ({ value, label: FORMAT_NAMES[value] }))
const minDate = computed(() => todayIn(timezone))
const selectedCount = computed(() => events.filter((e) => e.selected).length)

const loading = ref(false)
const progress = ref('')

/** Errors of events.N.* fields refer to the N-th selected event. */
const eventErrors = computed(() => {
  const selected = events.filter((e) => e.selected)
  const result: Partial<Record<EventId, string>> = {}
  for (const [field, message] of Object.entries(fieldErrors.value)) {
    const match = field.match(/^events\.(\d+)\./)
    const event = match && selected[Number(match[1])]
    if (event) {
      result[event.eventId] = message
    }
  }
  return result
})

async function submit() {
  clearErrors()
  const selected = events.filter((e) => e.selected)
  // Checked before generating scrambles, which takes a while; the server checks the same.
  const errors: Record<string, string> = {}
  if (!form.place.trim()) {
    errors.place = 'Укажите место'
  }
  if (selected.length === 0) {
    errors.events = 'Выберите хотя бы одну дисциплину'
  }
  if (Object.keys(errors).length) {
    fieldErrors.value = errors
    return
  }

  loading.value = true
  try {
    const scrambles = await generateScrambles(selected, (done, total) => {
      progress.value = `Генерируем скрамблы: ${done} из ${total}`
    })
    progress.value = 'Создаём встречу…'
    const meetup = await createMeetup(clubId, {
      ...form,
      events: selected.map((e, i) => ({
        event_id: e.eventId,
        format: e.format,
        scrambles: scrambles[i],
      })),
    })
    emit('created', meetup)
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
    progress.value = ''
  }
}
</script>

<template>
  <form class="meetup-form" novalidate @submit.prevent="submit">
    <section class="meetup-form__section">
      <h2 class="meetup-form__heading">Основные данные</h2>
      <AppCard class="meetup-form__fields">
        <AppInput v-model="form.date" label="Дата" type="date" :min="minDate" :error="fieldErrors.date" />
        <div class="meetup-form__row">
          <AppInput
            v-model="form.starts_at"
            label="Время начала"
            type="time"
            :error="fieldErrors.starts_at"
          />
          <AppInput
            v-model="form.ends_at"
            label="Время окончания"
            type="time"
            :error="fieldErrors.ends_at"
          />
        </div>
        <AppInput v-model="form.place" label="Место" :error="fieldErrors.place" />
        <AppInput
          v-model="form.address"
          label="Адрес"
          hint="Необязательно"
          :error="fieldErrors.address"
        />
      </AppCard>
    </section>

    <section class="meetup-form__section">
      <div class="meetup-form__heading-row">
        <div>
          <h2 class="meetup-form__heading">Дисциплины</h2>
          <p class="meetup-form__note">Выберите дисциплины встречи и формат результатов</p>
        </div>
        <span class="meetup-form__counter">{{ selectedCount }}/{{ EVENT_IDS.length }}</span>
      </div>
      <AppCard>
        <ul class="meetup-form__events">
          <li v-for="event in events" :key="event.eventId" class="meetup-form__event">
            <div class="meetup-form__event-row">
              <label class="meetup-form__checkbox">
                <input v-model="event.selected" type="checkbox" />
                {{ EVENTS[event.eventId].fullName }}
              </label>
              <AppSelect
                v-model="event.format"
                class="meetup-form__format"
                :options="formatOptions"
                :aria-label="`Формат: ${EVENTS[event.eventId].fullName}`"
                :disabled="!event.selected"
              />
            </div>
            <p v-if="event.selected && eventErrors[event.eventId]" class="meetup-form__error">
              {{ eventErrors[event.eventId] }}
            </p>
          </li>
        </ul>
      </AppCard>
      <p v-if="fieldErrors.events" class="meetup-form__error">{{ fieldErrors.events }}</p>
      <p class="meetup-form__note">
        Скрамблы будут сгенерированы автоматически при создании встречи.
      </p>
    </section>

    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="meetup-form__submit" :loading="loading">
      {{ progress || 'Создать встречу' }}
    </AppButton>
  </form>
</template>

<style scoped>
.meetup-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.meetup-form__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.meetup-form__heading {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.meetup-form__heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.meetup-form__note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.meetup-form__counter {
  flex-shrink: 0;
  padding: 2px var(--space-2);
  background: color-mix(in srgb, var(--color-primary) 12%, var(--color-surface));
  border-radius: var(--radius-badge);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.meetup-form__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.meetup-form__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.meetup-form__events {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.meetup-form__event-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.meetup-form__checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
}

.meetup-form__checkbox input {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin: 0;
  accent-color: var(--color-primary);
}

.meetup-form__format {
  flex-shrink: 0;
  width: 170px;
}

.meetup-form__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.meetup-form__submit {
  width: 100%;
}
</style>
