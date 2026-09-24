<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import {
  ATTEMPTS_COUNT,
  DNF,
  EVENTS,
  eventName,
  formatName,
  formatResult,
  plural,
  type EventId,
  type ResultType,
} from '@/shared/lib'
import { AppIcon } from '@/shared/ui'
import type { MeetupEvent } from '../model/types'

// Карточка дисциплины на странице встречи: статус и результат текущего
// пользователя, лидер таблицы. Действие («Собрать», «Продолжить») — в слоте.
const { event, resultsTo } = defineProps<{
  event: MeetupEvent
  /** Страница таблицы дисциплины. */
  resultsTo: RouteLocationRaw
}>()

const resultType = computed<ResultType>(
  () => EVENTS[event.event_id as EventId]?.resultType ?? 'time',
)
const isAverageFormat = computed(() => event.format === 'ao5' || event.format === 'mo3')

function show(value: number | null, isAverage: boolean): string {
  const text = formatResult(value, resultType.value, isAverage)
  return resultType.value === 'moves' && value !== null && value !== DNF ? `${text} ходов` : text
}

// Итог завершённой серии: среднее для ao5 и mo3, иначе лучшая попытка.
const myResult = computed(() => {
  const series = event.my_series
  if (series?.status !== 'completed') {
    return null
  }
  const value = isAverageFormat.value ? series.average : series.best
  return { text: show(value, isAverageFormat.value), isDnf: value === DNF }
})

</script>

<template>
  <article class="event-card">
    <div class="event-card__top">
      <div>
        <h3 class="event-card__name">{{ eventName(event.event_id) }}</h3>
        <p class="event-card__format">{{ formatName(event.format) }}</p>
      </div>
      <RouterLink :to="resultsTo" class="event-card__table">
        Таблица
        <AppIcon name="chevron-right" :size="18" />
      </RouterLink>
    </div>

    <div class="event-card__bottom">
      <div v-if="myResult && event.my_series" class="event-card__stats">
        <div>
          <p class="event-card__label">Ваш результат</p>
          <p :class="['event-card__value', { 'event-card__value--dnf': myResult.isDnf }]">
            {{ myResult.text }}
          </p>
        </div>
        <div>
          <p class="event-card__label">Место</p>
          <p class="event-card__value">
            <template v-if="event.my_series.place">
              {{ event.my_series.place }}
              <span class="event-card__of">из {{ event.my_series.total }}</span>
            </template>
            <template v-else>—</template>
          </p>
        </div>
      </div>
      <div v-else-if="event.my_series">
        <p class="event-card__label">Прогресс серии</p>
        <p class="event-card__text">
          {{ event.my_series.attempts_done }} из
          {{ plural(ATTEMPTS_COUNT[event.format], ['попытки', 'попыток', 'попыток']) }}
        </p>
      </div>
      <div v-else>
        <p class="event-card__label">Статус</p>
        <p class="event-card__text">
          {{ plural(event.participants_count, ['участник', 'участника', 'участников']) }}
        </p>
      </div>
      <slot name="action" />
    </div>

    <p v-if="event.leader" class="event-card__leader">
      <AppIcon name="leaderboard" :size="16" />
      <span>
        Лучший:
        <span class="event-card__mono">{{ show(event.leader.value, event.leader.is_average) }}</span>
        · {{ event.leader.display_name }}
      </span>
    </p>
  </article>
</template>

<style scoped>
.event-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.event-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.event-card__name {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.event-card__format,
.event-card__label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.event-card__table {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  color: var(--color-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.event-card__bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
}

.event-card__stats {
  display: flex;
  gap: var(--space-5);
}

.event-card__value {
  font-family: var(--font-mono);
  font-size: var(--font-size-time-large);
  font-weight: var(--font-weight-time-large);
  font-variant-numeric: tabular-nums;
}

.event-card__value--dnf {
  color: var(--color-dnf);
}

.event-card__of {
  color: var(--color-text-secondary);
  font-family: var(--font-sans);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-body);
}

.event-card__text {
  color: var(--color-text-secondary);
}

.event-card__leader {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.event-card__mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.event-card__leader svg {
  flex-shrink: 0;
}
</style>
