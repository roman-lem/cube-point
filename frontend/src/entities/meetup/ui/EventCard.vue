<script setup lang="ts">
import { eventName, formatName, plural, type SeriesFormat } from '@/shared/lib'

// Карточка дисциплины на странице встречи. Результаты участника и лучший
// результат появятся вместе с сериями; действие («Собрать») — в слоте.
defineProps<{
  eventId: string
  format: SeriesFormat
  participantsCount: number
}>()
</script>

<template>
  <article class="event-card">
    <div>
      <h3 class="event-card__name">{{ eventName(eventId) }}</h3>
      <p class="event-card__format">{{ formatName(format) }}</p>
    </div>
    <div class="event-card__bottom">
      <div>
        <p class="event-card__label">Статус</p>
        <p class="event-card__count">
          {{ plural(participantsCount, ['участник', 'участника', 'участников']) }}
        </p>
      </div>
      <slot name="action" />
    </div>
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

.event-card__name {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.event-card__format,
.event-card__label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.event-card__bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
}

.event-card__count {
  color: var(--color-text-secondary);
}
</style>
