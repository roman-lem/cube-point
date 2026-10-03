<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ApiError } from '@/shared/api'
import { latestLoader, usePolling } from '@/shared/lib'
import { AppButton, AppCard, AppIcon } from '@/shared/ui'
import {
  approveAll, approveRequest, fetchRequests, rejectRequest, type ParticipationRequest,
} from '../api/requestsApi'

// Participation requests for the meetup. People send them right at the meetup,
// so the list refreshes itself every 10 seconds (not for a finished meetup).
const { meetupId, readonly = false } = defineProps<{
  meetupId: number
  /** The meetup is finished: requests are read-only. */
  readonly?: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const REFRESH_MS = 10_000

const requests = ref<ParticipationRequest[]>([])
const loaded = ref(false)
const busyUserId = ref<number | null>(null)
const approvingAll = ref(false)
/** Error of the last action (approve, reject). */
const error = ref('')
/** Error of loading the list: cleared by the next successful load. */
const loadError = ref('')

const pendingCount = computed(() => requests.value.filter((r) => r.status === 'pending').length)
const approvedCount = computed(() => requests.value.filter((r) => r.status === 'approved').length)

const { load } = latestLoader(
  () => fetchRequests(meetupId),
  (list) => {
    requests.value = list
    loaded.value = true
    loadError.value = ''
  },
  (e) => {
    loadError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить заявки'
  },
)

onMounted(load)
usePolling(load, REFRESH_MS, () => !readonly)

async function run(action: () => Promise<unknown>, userId: number | null) {
  error.value = ''
  busyUserId.value = userId
  try {
    await action()
    await load()
    emit('changed')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось сохранить, попробуйте ещё раз'
    await load()
  } finally {
    busyUserId.value = null
  }
}

function approve(userId: number) {
  return run(() => approveRequest(meetupId, userId), userId)
}

function reject(userId: number) {
  return run(() => rejectRequest(meetupId, userId), userId)
}

async function onApproveAll() {
  approvingAll.value = true
  await run(() => approveAll(meetupId), null)
  approvingAll.value = false
}

const STATUS_NAMES = { approved: 'Подтверждена', rejected: 'Отклонена' } as const
</script>

<template>
  <AppCard class="requests">
    <div class="requests__header">
      <div>
        <h2 class="requests__title">
          Заявки
          <span v-if="pendingCount" class="requests__badge">{{ pendingCount }}</span>
        </h2>
        <p class="requests__note">Подтверждено: {{ approvedCount }}</p>
      </div>
      <AppButton
        v-if="!readonly && pendingCount > 1"
        variant="secondary"
        :loading="approvingAll"
        @click="onApproveAll"
      >
        Подтвердить всех
      </AppButton>
    </div>

    <p v-if="error || loadError" class="requests__error" role="alert">{{ error || loadError }}</p>
    <p v-if="loaded && requests.length === 0" class="requests__note">
      Заявок пока нет. Покажите участникам QR-код встречи.
    </p>

    <ul class="requests__list">
      <li v-for="request in requests" :key="request.user.id" class="requests__item">
        <div class="requests__person">
          <p class="requests__name">{{ request.user.display_name }}</p>
          <p class="requests__login">{{ request.user.login }}</p>
        </div>
        <template v-if="request.status === 'pending' && !readonly">
          <div class="requests__actions">
            <AppButton
              variant="secondary"
              :disabled="busyUserId !== null"
              :aria-label="`Отклонить: ${request.user.display_name}`"
              @click="reject(request.user.id)"
            >
              Отклонить
            </AppButton>
            <AppButton
              :loading="busyUserId === request.user.id"
              :disabled="busyUserId !== null"
              :aria-label="`Подтвердить: ${request.user.display_name}`"
              @click="approve(request.user.id)"
            >
              <AppIcon name="check" :size="20" />
              Подтвердить
            </AppButton>
          </div>
        </template>
        <div v-else-if="request.status !== 'pending'" class="requests__status">
          <span :class="`requests__status--${request.status}`">
            {{ STATUS_NAMES[request.status] }}
          </span>
          <button
            v-if="request.status === 'rejected' && !readonly"
            type="button"
            class="requests__link"
            :disabled="busyUserId !== null"
            @click="approve(request.user.id)"
          >
            Подтвердить
          </button>
        </div>
        <span v-else class="requests__status">Ожидает</span>
      </li>
    </ul>
  </AppCard>
</template>

<style scoped>
.requests {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.requests__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.requests__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.requests__badge {
  min-width: 24px;
  padding: 0 6px;
  background: var(--color-primary);
  border-radius: var(--radius-badge);
  color: var(--color-on-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  text-align: center;
}

.requests__note,
.requests__login {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.requests__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.requests__list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.requests__item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--color-border);
}

.requests__person {
  min-width: 0;
}

.requests__name {
  font-weight: var(--font-weight-label);
}

.requests__actions {
  display: flex;
  gap: var(--space-2);
}

.requests__status {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.requests__status--approved {
  color: var(--color-text-primary);
}

.requests__link {
  padding: 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}
</style>
