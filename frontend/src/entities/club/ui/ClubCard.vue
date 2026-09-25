<script setup lang="ts">
import { formatDate, plural } from '@/shared/lib'
import type { ClubSummary } from '../model/types'

// Карточка клуба в списках клубов (лендинг, страница всех клубов).
defineProps<{ club: ClubSummary }>()
</script>

<template>
  <RouterLink :to="{ name: 'club', params: { clubId: club.id } }" class="club-card">
    <div class="club-card__head">
      <span class="club-card__name">{{ club.name }}</span>
      <span class="club-card__city">{{ club.city }}</span>
    </div>
    <p class="club-card__stats">
      {{ plural(club.member_count, ['участник', 'участника', 'участников']) }} ·
      {{ plural(club.meetup_count, ['встреча', 'встречи', 'встреч']) }}
    </p>
    <p v-if="club.last_meetup_date" class="club-card__last">
      последняя встреча {{ formatDate(club.last_meetup_date) }}
    </p>
  </RouterLink>
</template>

<style scoped>
.club-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-text-primary);
  text-decoration: none;
}

.club-card:hover {
  border-color: var(--color-primary);
}

.club-card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-1) var(--space-3);
}

.club-card__name {
  font-weight: var(--font-weight-label);
}

.club-card__city,
.club-card__last {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.club-card__stats,
.club-card__last {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.club-card__stats {
  font-size: var(--font-size-label);
}

.club-card__last {
  font-size: 12px;
}
</style>
