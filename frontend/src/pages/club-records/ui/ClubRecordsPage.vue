<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TimeValue } from '@/entities/attempt'
import { fetchClub, useCurrentClubStore, type ClubPageData } from '@/entities/club'
import {
  fetchClubRecords, RecordBadge, type ClubEventRecords, type RecordType,
} from '@/entities/record'
import { ApiError } from '@/shared/api'
import { EVENTS, eventName, formatDate, movesWord, type EventId } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'

// Рекорды клуба (макет club_records): лучшая сборка или среднее по дисциплинам.
// Правила — раздел «Рекорды» CLAUDE.md.
const { clubId } = defineProps<{ clubId: number }>()

const clubStore = useCurrentClubStore()
const club = ref<ClubPageData | null>(null)
const records = ref<ClubEventRecords[] | null>(null)
const error = ref('')
const type = ref<RecordType>('single')

const TYPES: { value: RecordType; label: string }[] = [
  { value: 'single', label: 'Лучшая сборка' },
  { value: 'average', label: 'Среднее' },
]

watch(
  () => clubId,
  async (id) => {
    error.value = ''
    records.value = null
    clubStore.setClubId(id)
    try {
      ;[club.value, records.value] = await Promise.all([fetchClub(id), fetchClubRecords(id)])
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить рекорды'
    }
  },
  { immediate: true },
)

// У дисциплин, где все встречи были в bo-форматах, среднего нет — их в «Среднем» не показываем.
const rows = computed(() =>
  (records.value ?? []).filter((event) => event[type.value] !== null),
)

const resultType = (eventId: string) => EVENTS[eventId as EventId]?.resultType ?? 'time'
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Рекорды клуба" :subtitle="club?.club.name" />

    <AppCard v-if="error">{{ error }}</AppCard>

    <template v-else-if="records">
      <div class="club-records__switch" role="tablist" aria-label="Вид рекорда">
        <button
          v-for="item in TYPES"
          :key="item.value"
          type="button"
          role="tab"
          :aria-selected="type === item.value"
          :class="['club-records__switch-item', { 'club-records__switch-item--active': type === item.value }]"
          @click="type = item.value"
        >
          {{ item.label }}
        </button>
      </div>

      <AppCard v-if="rows.length === 0" class="page__muted">
        {{ records.length ? 'Рекордов по среднему пока нет' : 'Рекордов пока нет — они появятся после первой встречи' }}
      </AppCard>

      <ul v-else class="club-records__list">
        <li v-for="event in rows" :key="event.event_id">
          <AppCard class="club-records__card">
            <div class="club-records__head">
              <h2 class="club-records__event">{{ eventName(event.event_id) }}</h2>
              <span class="club-records__value">
                <RecordBadge mark="LR" />
                <TimeValue
                  :value="event[type]!.value"
                  :result-type="resultType(event.event_id)"
                  :is-average="type === 'average'"
                  size="large"
                />
                <span v-if="resultType(event.event_id) === 'moves'" class="club-records__unit">
                  {{ movesWord(event[type]!.value, type === 'average') }}
                </span>
              </span>
            </div>
            <p class="club-records__who">
              <RouterLink :to="{ name: 'user-profile', params: { userId: event[type]!.user.id } }">
                {{ event[type]!.user.display_name }}
              </RouterLink>
              <RouterLink
                class="club-records__date"
                :to="{ name: 'meetup', params: { meetupId: event[type]!.meetup.id } }"
              >
                {{ formatDate(event[type]!.meetup.date) }}
              </RouterLink>
            </p>
          </AppCard>
        </li>
      </ul>

      <p class="club-records__note">
        LR — рекорд клуба: лучший результат за всю историю встреч клуба.
        При равенстве рекорд остаётся за тем, кто поставил его первым.
      </p>
    </template>
  </main>
</template>

<style scoped>
.club-records__switch {
  display: flex;
  padding: var(--space-1);
  background: var(--color-border);
  border-radius: var(--radius-button);
}

.club-records__switch-item {
  flex: 1;
  height: 36px;
  background: none;
  border: none;
  border-radius: 6px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.club-records__switch-item--active {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.club-records__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.club-records__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.club-records__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.club-records__event {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-heading);
}

.club-records__value {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.club-records__unit {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.club-records__who {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--font-size-label);
}

.club-records__date {
  color: var(--color-text-secondary);
}

.club-records__note {
  color: var(--color-text-secondary);
  font-size: 13px;
}
</style>
