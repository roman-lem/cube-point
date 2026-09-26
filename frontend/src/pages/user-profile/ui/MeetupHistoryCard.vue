<script setup lang="ts">
import { TimeValue } from '@/entities/attempt'
import { RecordBadge } from '@/entities/record'
import { AttemptSeries } from '@/entities/series'
import type { ProfileEventResult, ProfileMeetup } from '@/entities/user'
import { EVENTS, eventName, formatDate, movesWord, plural } from '@/shared/lib'
import { AppCard, AppIcon } from '@/shared/ui'

// A meetup in the profile history: results per event with attempts (in bo1 the attempt
// is the result, so the attempt row is shown only if an organizer corrected it).
// AttemptSeries marks attempts corrected by an organizer; PB and LR marks are
// shown only for current records.
const { meetup, showClub = false } = defineProps<{
  meetup: ProfileMeetup
  /** The person attends several clubs: show which club the meetup was in. */
  showClub?: boolean
}>()

/** The main result of a series: the average for ao5/mo3, otherwise the best attempt. */
function main(result: ProfileEventResult) {
  const isAverage = result.format === 'ao5' || result.format === 'mo3'
  return {
    value: isAverage ? result.average : result.best,
    isAverage,
    marks: isAverage ? result.marks.average : result.marks.single,
  }
}

const resultType = (result: ProfileEventResult) => EVENTS[result.event_id]?.resultType ?? 'time'
</script>

<template>
  <AppCard class="history-card">
    <RouterLink class="history-card__head" :to="{ name: 'meetup', params: { meetupId: meetup.id } }">
      <AppIcon name="schedule" :size="18" />
      <span class="history-card__date">{{ formatDate(meetup.date) }}</span>
      <span v-if="meetup.status === 'live'" class="history-card__live">идёт</span>
      <span class="history-card__meta">
        <template v-if="showClub">{{ meetup.club.name }} · </template>
        {{ plural(meetup.events.length, ['дисциплина', 'дисциплины', 'дисциплин']) }}
      </span>
    </RouterLink>

    <section v-for="result in meetup.events" :key="result.event_id" class="history-card__event">
      <div class="history-card__event-head">
        <h3 class="history-card__event-name">{{ eventName(result.event_id) }}</h3>
        <span class="history-card__result">
          <RecordBadge v-for="mark in main(result).marks" :key="mark" :mark="mark" />
          <span class="history-card__format">{{ result.format }}:</span>
          <TimeValue
            :value="main(result).value"
            :result-type="resultType(result)"
            :is-average="main(result).isAverage"
          />
          <span
            v-if="resultType(result) === 'moves' && main(result).value !== null && main(result).value! > 0"
            class="history-card__format"
          >
            {{ movesWord(main(result).value!, main(result).isAverage) }}
          </span>
        </span>
      </div>
      <p v-if="main(result).isAverage" class="history-card__single">
        лучшая: <TimeValue :value="result.best" :result-type="resultType(result)" />
        <RecordBadge v-for="mark in result.marks.single" :key="mark" :mark="mark" />
      </p>
      <AttemptSeries
        v-if="result.format !== 'bo1' || result.attempts[0]?.edited"
        :attempts="result.attempts"
        :format="result.format"
        :result-type="resultType(result)"
      />
    </section>
  </AppCard>
</template>

<style scoped>
.history-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.history-card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  color: inherit;
  text-decoration: none;
}

.history-card__date {
  font-weight: var(--font-weight-heading);
}

.history-card__live {
  padding: 1px 6px;
  background: var(--color-primary);
  border-radius: var(--radius-badge);
  color: var(--color-on-primary);
  font-size: 11px;
}

.history-card__meta {
  margin-left: auto;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.history-card__event {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.history-card__event-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.history-card__event-name {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-label);
}

.history-card__result {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.history-card__format {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.history-card__single {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 13px;
}
</style>
