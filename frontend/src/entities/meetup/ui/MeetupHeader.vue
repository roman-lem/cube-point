<script setup lang="ts">
import { computed } from 'vue'
import { formatDate, formatTimeRange, plural } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'
import type { Meetup } from '../model/types'
import MeetupStatusBadge from './MeetupStatusBadge.vue'

const { meetup } = defineProps<{ meetup: Meetup }>()

const details = computed(() => {
  const parts = [
    formatTimeRange(meetup.starts_at, meetup.ends_at, meetup.club.timezone),
    plural(meetup.participants_count, ['участник', 'участника', 'участников']),
  ]
  if (meetup.place) {
    parts.unshift(meetup.place)
  }
  return parts.join(' · ')
})
</script>

<template>
  <header class="meetup-header">
    <div class="meetup-header__top">
      <p class="meetup-header__club">{{ meetup.club.name }}</p>
      <MeetupStatusBadge :status="meetup.status" />
    </div>
    <h1 class="meetup-header__title">Встреча клуба, {{ formatDate(meetup.date) }}</h1>
    <p class="meetup-header__details">
      <AppIcon name="location" :size="18" />
      <span>{{ details }}</span>
    </p>
    <p v-if="meetup.address" class="meetup-header__address">{{ meetup.address }}</p>
  </header>
</template>

<style scoped>
.meetup-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.meetup-header__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.meetup-header__club {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.meetup-header__title {
  font-size: var(--font-size-heading);
  font-weight: var(--font-weight-heading);
  line-height: 1.3;
}

.meetup-header__details {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.meetup-header__details svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.meetup-header__address {
  padding-left: 22px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}
</style>
