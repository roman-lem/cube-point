<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Meetup } from '@/entities/meetup'
import { ApiError } from '@/shared/api'
import {
  FMC_DNF_REASONS, checkSolution, eventName, formatTime, plural, preloadSolutionCheck,
} from '@/shared/lib'
import { AppButton, AppIcon, ConfirmDialog } from '@/shared/ui'
import {
  fetchFinishSummary, finishMeetup, resolveFmc, type FinishSummary, type UnresolvedFmc,
} from '../api/finishApi'

// Finishing a meetup: summary of unfinished series and unsubmitted FMC attempts,
// which the organizer checks in their browser or counts as DNF.
const { meetup } = defineProps<{ meetup: Meetup }>()
const emit = defineEmits<{ finished: [meetup: Meetup] }>()

const open = ref(false)
const summary = ref<FinishSummary | null>(null)
const finishing = ref(false)
const busyKey = ref<string | null>(null)
/** Outcomes of resolved FMC attempts: "Анна Иванова — 28 ходов". */
const resolved = ref<string[]>([])
const error = ref('')

const STATE_NAMES = {
  frozen: 'Сдача не подтверждена',
  expired: 'Время вышло без сдачи',
  running: 'Время ещё идёт',
} as const

const itemKey = (item: UnresolvedFmc) => `${item.series_id}:${item.attempt_number}`
const hasFmc = computed(() => Boolean(summary.value?.fmc.length))

function message(e: unknown, fallback: string) {
  return e instanceof ApiError ? e.message : fallback
}

async function load() {
  try {
    summary.value = await fetchFinishSummary(meetup.id)
  } catch (e) {
    error.value = message(e, 'Не удалось загрузить сводку')
  }
}

async function openDialog() {
  error.value = ''
  resolved.value = []
  summary.value = null
  open.value = true
  preloadSolutionCheck()
  await load()
}

async function check(item: UnresolvedFmc) {
  busyKey.value = itemKey(item)
  error.value = ''
  try {
    const result = await checkSolution(item.scramble, item.solution)
    if ('moves' in result) {
      await resolveFmc(meetup.id, item, { value: result.moves, penalty: 'none' })
      resolved.value.push(`${item.user.display_name} — ${plural(result.moves, ['ход', 'хода', 'ходов'])}`)
    } else {
      await resolveFmc(meetup.id, item, { value: null, penalty: 'dnf' })
      resolved.value.push(`${item.user.display_name} — DNF: ${FMC_DNF_REASONS[result.dnf]}`)
    }
  } catch (e) {
    error.value = message(e, 'Не удалось проверить решение')
  } finally {
    busyKey.value = null
    await load()
  }
}

async function markDnf(item: UnresolvedFmc) {
  busyKey.value = itemKey(item)
  error.value = ''
  try {
    await resolveFmc(meetup.id, item, { value: null, penalty: 'dnf' })
    resolved.value.push(`${item.user.display_name} — DNF`)
  } catch (e) {
    error.value = message(e, 'Не удалось сохранить DNF')
  } finally {
    busyKey.value = null
    await load()
  }
}

async function finish() {
  finishing.value = true
  error.value = ''
  try {
    const finished = await finishMeetup(meetup.id)
    open.value = false
    emit('finished', finished)
  } catch (e) {
    error.value = message(e, 'Не удалось завершить встречу')
    await load()
  } finally {
    finishing.value = false
  }
}
</script>

<template>
  <AppButton variant="danger" class="finish-meetup" @click="openDialog">
    <AppIcon name="stop" :size="20" />
    Завершить встречу
  </AppButton>
  <ConfirmDialog
    v-model:open="open"
    title="Завершить встречу?"
    confirm-label="Завершить"
    danger
    wide
    :loading="finishing"
    :confirm-disabled="!summary || hasFmc"
    @confirm="finish"
  >
    <div class="finish-meetup__body">
      <p v-if="!summary && !error">Загружаем сводку…</p>
      <template v-if="summary">
        <p v-if="summary.unfinished.length === 0">Все начатые серии завершены.</p>
        <template v-else>
          <p>
            Незавершённые серии у
            {{ plural(summary.unfinished.length, ['участника', 'участников', 'участников']) }}.
            Несобранные попытки станут DNS
            ({{ plural(summary.dns_count, ['попытка', 'попытки', 'попыток']) }}).
          </p>
          <ul class="finish-meetup__list">
            <li v-for="item in summary.unfinished" :key="item.user.id">
              <span class="finish-meetup__name">{{ item.user.display_name }}</span>
              <span class="finish-meetup__events">
                <span v-for="event in item.events" :key="event.event_id">
                  {{ eventName(event.event_id) }}
                  <span class="finish-meetup__mono">{{ event.attempts_done }}/{{ event.attempts_count }}</span>
                </span>
              </span>
            </li>
          </ul>
        </template>
        <p>Ссылка на встречу перестанет работать, участники больше не смогут сдавать попытки.</p>

        <section v-if="hasFmc" class="finish-meetup__fmc">
          <h3 class="finish-meetup__subtitle">Несданные попытки FMC</h3>
          <p>
            Их нужно разрешить до завершения: проверить решение (так же, как у участника)
            или засчитать DNF. Если время ещё идёт, можно подождать и обновить сводку.
          </p>
          <article v-for="item in summary.fmc" :key="itemKey(item)" class="finish-meetup__item">
            <p class="finish-meetup__item-head">
              <span class="finish-meetup__name">{{ item.user.display_name }}</span>
              <span v-if="item.attempt_number > 1">· попытка {{ item.attempt_number }}</span>
              <span class="finish-meetup__state">
                {{ STATE_NAMES[item.state] }}
                <template v-if="item.state === 'running'">
                  до {{ formatTime(item.deadline, meetup.club.timezone) }}
                </template>
              </span>
            </p>
            <p class="finish-meetup__label">Скрамбл</p>
            <p class="finish-meetup__mono">{{ item.scramble }}</p>
            <p class="finish-meetup__label">Решение</p>
            <p class="finish-meetup__mono">{{ item.solution || 'пусто' }}</p>
            <div class="finish-meetup__actions">
              <AppButton
                v-if="item.state !== 'running'"
                :loading="busyKey === itemKey(item)"
                :disabled="busyKey !== null"
                @click="check(item)"
              >
                Проверить
              </AppButton>
              <AppButton v-else variant="secondary" :disabled="busyKey !== null" @click="load">
                <AppIcon name="refresh" :size="20" />
                Обновить
              </AppButton>
              <AppButton variant="danger" :disabled="busyKey !== null" @click="markDnf(item)">
                DNF
              </AppButton>
            </div>
          </article>
        </section>
        <ul v-if="resolved.length" class="finish-meetup__resolved">
          <li v-for="line in resolved" :key="line">
            <AppIcon name="check" :size="16" />
            {{ line }}
          </li>
        </ul>
      </template>
      <p v-if="error" class="finish-meetup__error" role="alert">{{ error }}</p>
    </div>
  </ConfirmDialog>
</template>

<style scoped>
.finish-meetup {
  width: 100%;
}

.finish-meetup__body,
.finish-meetup__fmc {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.finish-meetup__list,
.finish-meetup__resolved {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.finish-meetup__list li {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-1) var(--space-3);
}

.finish-meetup__name {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-label);
}

.finish-meetup__events {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.finish-meetup__mono {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.finish-meetup__subtitle {
  color: var(--color-text-primary);
  font-size: 16px;
  font-weight: var(--font-weight-heading);
}

.finish-meetup__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.finish-meetup__item-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-2);
}

.finish-meetup__state {
  margin-left: auto;
  font-size: var(--font-size-label);
}

.finish-meetup__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.finish-meetup__actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.finish-meetup__resolved li {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
}

.finish-meetup__error {
  color: var(--color-danger);
}
</style>
