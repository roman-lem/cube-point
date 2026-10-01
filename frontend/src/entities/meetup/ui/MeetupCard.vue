<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { eventName, formatDate, formatTime, plural } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'
import type { MeetupSummary } from '../model/types'
import MeetupStatusBadge from './MeetupStatusBadge.vue'

// full: the upcoming meetup, large; compact: a row in the list of past ones.
const { meetup, variant = 'full' } = defineProps<{
  meetup: MeetupSummary
  timezone: string
  to: RouteLocationRaw
  variant?: 'full' | 'compact'
}>()

const PARTICIPANTS: [string, string, string] = ['участник', 'участника', 'участников']

const cancelled = computed(() => meetup.status === 'cancelled')
</script>

<template>
  <RouterLink
    v-if="variant === 'compact'"
    :to="to"
    :class="['meetup-card', 'meetup-card--compact', { 'meetup-card--cancelled': cancelled }]"
  >
    <div class="meetup-card__text">
      <p class="meetup-card__line">
        <span class="meetup-card__date">{{ formatDate(meetup.date) }}</span>
        <span class="meetup-card__dot">•</span>
        <span>{{ plural(meetup.participants_count, PARTICIPANTS) }}</span>
        <MeetupStatusBadge
          v-if="meetup.status === 'live' || cancelled"
          :status="meetup.status"
        />
      </p>
      <p class="meetup-card__events">{{ meetup.events.map(eventName).join(', ') }}</p>
    </div>
    <AppIcon name="chevron-right" class="meetup-card__chevron" />
  </RouterLink>

  <article v-else :class="['meetup-card', { 'meetup-card--cancelled': cancelled }]">
    <MeetupStatusBadge :status="meetup.status" />
    <h3 class="meetup-card__title">
      {{ formatDate(meetup.date) }}, {{ formatTime(meetup.starts_at, timezone) }}
    </h3>
    <div v-if="meetup.place" class="meetup-card__place">
      <AppIcon name="location" :size="20" />
      <div>
        <p>{{ meetup.place }}</p>
        <p v-if="meetup.address" class="meetup-card__address">{{ meetup.address }}</p>
      </div>
    </div>
    <ul class="meetup-card__chips">
      <li v-for="eventId in meetup.events" :key="eventId" class="meetup-card__chip">
        {{ eventName(eventId) }}
      </li>
    </ul>
    <p v-if="meetup.participants_count > 0 && !cancelled" class="meetup-card__address">
      {{ plural(meetup.participants_count, PARTICIPANTS) }}
    </p>
    <RouterLink :to="to" class="meetup-card__more">
      Подробнее о встрече
      <AppIcon name="chevron-right" :size="20" />
    </RouterLink>
  </article>
</template>

<style scoped>
.meetup-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.meetup-card__title {
  font-size: var(--font-size-heading);
  font-weight: var(--font-weight-heading);
}

.meetup-card__place {
  display: flex;
  gap: var(--space-2);
}

.meetup-card__place svg {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--color-text-secondary);
}

.meetup-card__address,
.meetup-card__events {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-body);
}

.meetup-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.meetup-card__chip {
  padding: 2px var(--space-2);
  background: var(--color-background);
  border-radius: var(--radius-badge);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
}

.meetup-card__more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  width: 100%;
  height: var(--control-height);
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-label);
  text-decoration: none;
}

.meetup-card--compact {
  flex-direction: row;
  align-items: center;
  color: inherit;
  text-decoration: none;
}

.meetup-card--compact:hover {
  border-color: var(--color-primary);
}

.meetup-card__text {
  flex: 1;
  min-width: 0;
}

.meetup-card__line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.meetup-card__date {
  font-weight: var(--font-weight-label);
}

.meetup-card__dot {
  color: var(--color-text-secondary);
}

.meetup-card__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

/* A cancelled meetup stays in the list, muted. */
.meetup-card--cancelled {
  background: var(--color-background);
  color: var(--color-text-secondary);
}

.meetup-card--cancelled .meetup-card__chip,
.meetup-card--cancelled .meetup-card__more {
  background: var(--color-surface);
}
</style>
