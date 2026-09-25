<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MeetupDesk } from '@/entities/meetup'
import { DisqualificationControl } from '@/features/disqualification'
import { ATTEMPTS_COUNT, eventName } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'

// Участники встречи с компактным статусом по дисциплинам (макет org_meetup):
// «3x3 ✓ · 2x2 3/5 · OH —». Нажатие — ручной ввод результатов участника.
const { meetupId, desk, editable } = defineProps<{
  meetupId: number
  desk: MeetupDesk
  /** Можно вводить результаты (встреча запущена). */
  editable: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const query = ref('')

const participants = computed(() => {
  const text = query.value.trim().toLocaleLowerCase('ru')
  return desk.participants.filter(
    (p) =>
      !text ||
      p.user.display_name.toLocaleLowerCase('ru').includes(text) ||
      p.user.login.includes(text),
  )
})

function statuses(userId: number) {
  return desk.events.map((event) => {
    const series = event.rows.find((row) => row.user.id === userId)?.series
    const count = ATTEMPTS_COUNT[event.format]
    const done = series?.attempts.filter(Boolean).length ?? 0
    return {
      eventId: event.event_id,
      name: eventName(event.event_id),
      state: !series ? '—' : series.status === 'completed' ? '✓' : `${done}/${count}`,
      completed: series?.status === 'completed',
    }
  })
}

function initials(name: string) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
}
</script>

<template>
  <div class="participant-list">
    <label class="participant-list__search">
      <AppIcon name="search" :size="20" />
      <input v-model="query" type="search" placeholder="Поиск участника" aria-label="Поиск участника" />
    </label>

    <ul class="participant-list__items">
      <li v-for="p in participants" :key="p.user.id" class="participant-list__item">
        <component
          :is="editable ? 'RouterLink' : 'div'"
          class="participant-list__main"
          v-bind="editable ? { to: { name: 'series-edit', params: { meetupId, userId: p.user.id } } } : {}"
        >
          <span class="participant-list__avatar" aria-hidden="true">{{ initials(p.user.display_name) }}</span>
          <span class="participant-list__who">
            <span class="participant-list__name">{{ p.user.display_name }}</span>
            <span class="participant-list__events">
              <span
                v-for="status in statuses(p.user.id)"
                :key="status.eventId"
                :class="{ 'participant-list__event--done': status.completed }"
              >
                {{ status.name }} <span class="participant-list__mono">{{ status.state }}</span>
              </span>
            </span>
          </span>
          <AppIcon v-if="editable" name="chevron-right" :size="20" class="participant-list__chevron" />
        </component>
        <DisqualificationControl
          :meetup-id="meetupId"
          :user="p.user"
          :disqualification="p.disqualification"
          compact
          @changed="emit('changed')"
        />
      </li>
      <li v-if="participants.length === 0" class="participant-list__empty">
        {{ desk.participants.length ? 'Никого не нашли' : 'Подтверждённых участников пока нет' }}
      </li>
    </ul>
    <p v-if="editable && desk.participants.length" class="participant-list__hint">
      Нажмите на участника для ручного ввода или правки попыток
    </p>
  </div>
</template>

<style scoped>
.participant-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.participant-list__search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
}

.participant-list__search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.participant-list__search input {
  flex: 1;
  min-width: 0;
  background: none;
  border: none;
  outline: none;
  color: var(--color-text-primary);
}

.participant-list__items {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  list-style: none;
}

.participant-list__item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding-right: var(--space-1);
  border-top: 1px solid var(--color-border);
}

.participant-list__item:first-child {
  border-top: none;
}

.participant-list__main {
  display: flex;
  flex: 1;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3);
  color: inherit;
  text-decoration: none;
}

.participant-list__avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--color-background);
  border-radius: 50%;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.participant-list__who {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.participant-list__name {
  font-weight: var(--font-weight-label);
}

.participant-list__events {
  display: flex;
  flex-wrap: wrap;
  gap: 0 var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.participant-list__event--done {
  color: var(--color-text-primary);
}

.participant-list__mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.participant-list__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.participant-list__empty,
.participant-list__hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.participant-list__empty {
  padding: var(--space-4);
  text-align: center;
}
</style>
