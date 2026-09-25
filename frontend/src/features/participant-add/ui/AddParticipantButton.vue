<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { ref, watch } from 'vue'
import { ApiError } from '@/shared/api'
import { AppButton, AppIcon, AppInput, TemporaryPassword } from '@/shared/ui'
import {
  addMember, addNewcomer, fetchCandidates, type AddedParticipant, type Candidate,
} from '../api/participantsApi'
import NewcomerForm from './NewcomerForm.vue'

// Ручное добавление участника на встречу (сразу подтверждённым): поиск среди
// участников клуба или новый аккаунт с временным паролем для пришедших без телефона.
const { meetupId } = defineProps<{ meetupId: number }>()
const emit = defineEmits<{ added: [] }>()

const dialog = ref<HTMLDialogElement>()
const mode = ref<'search' | 'new'>('search')
const query = ref('')
const candidates = ref<Candidate[]>([])
const busyId = ref<number | null>(null)
const created = ref<AddedParticipant | null>(null)
const error = ref('')

async function search() {
  try {
    candidates.value = await fetchCandidates(meetupId, query.value.trim())
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить участников клуба'
  }
}

watchDebounced(query, search, { debounce: 300 })
watch(mode, () => (error.value = ''))

function open() {
  mode.value = 'search'
  query.value = ''
  created.value = null
  error.value = ''
  dialog.value?.showModal()
  search()
}

function close() {
  dialog.value?.close()
}

async function add(candidate: Candidate) {
  busyId.value = candidate.user.id
  error.value = ''
  try {
    await addMember(meetupId, candidate.user.id)
    emit('added')
    await search()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось добавить участника'
  } finally {
    busyId.value = null
  }
}

const createNewcomer = (displayName: string, login: string) =>
  addNewcomer(meetupId, displayName, login)

function onCreated(result: AddedParticipant) {
  created.value = result
  emit('added')
}

const STATUS_NAMES = { approved: 'На встрече', pending: 'Ждёт подтверждения', rejected: 'Отклонён' }
</script>

<template>
  <AppButton variant="secondary" @click="open">
    <AppIcon name="person-add" :size="20" />
    Добавить участника
  </AppButton>

  <dialog ref="dialog" class="add-participant" @click.self="close">
    <div class="add-participant__body">
      <h2 class="add-participant__title">Добавить участника</h2>

      <template v-if="created">
        <p>
          Аккаунт создан, «{{ created.user.display_name }}» добавлен на встречу.
          Передайте логин и временный пароль — <strong>пароль показывается один раз</strong>.
          При первом входе его нужно будет сменить.
        </p>
        <TemporaryPassword :login="created.user.login" :password="created.temporary_password!" />
        <AppButton @click="close">Готово</AppButton>
      </template>

      <template v-else>
        <div class="add-participant__tabs" role="tablist">
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'search'"
            :class="['add-participant__tab', { 'add-participant__tab--active': mode === 'search' }]"
            @click="mode = 'search'"
          >
            Из клуба
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'new'"
            :class="['add-participant__tab', { 'add-participant__tab--active': mode === 'new' }]"
            @click="mode = 'new'"
          >
            Новый аккаунт
          </button>
        </div>

        <template v-if="mode === 'search'">
          <AppInput v-model="query" label="Имя или логин" placeholder="Поиск" autocomplete="off" />
          <ul class="add-participant__list">
            <li v-for="candidate in candidates" :key="candidate.user.id" class="add-participant__item">
              <div>
                <p class="add-participant__name">{{ candidate.user.display_name }}</p>
                <p class="add-participant__muted">{{ candidate.user.login }}</p>
              </div>
              <span v-if="candidate.status === 'approved'" class="add-participant__muted">
                {{ STATUS_NAMES.approved }}
              </span>
              <AppButton
                v-else
                variant="secondary"
                :loading="busyId === candidate.user.id"
                :disabled="busyId !== null"
                @click="add(candidate)"
              >
                Добавить
              </AppButton>
            </li>
            <li v-if="candidates.length === 0" class="add-participant__muted">
              Никого не нашли. Если человека нет в клубе, создайте новый аккаунт.
            </li>
          </ul>
        </template>

        <NewcomerForm
          v-else
          :create="createNewcomer"
          submit-label="Создать и добавить"
          @created="onCreated"
        />

        <p v-if="error" class="add-participant__error" role="alert">{{ error }}</p>
        <AppButton variant="secondary" @click="close">Закрыть</AppButton>
      </template>
    </div>
  </dialog>
</template>

<style scoped>
.add-participant {
  width: calc(100% - 2 * var(--page-padding));
  max-width: 480px;
  padding: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
}

.add-participant::backdrop {
  background: color-mix(in srgb, var(--color-text-primary) 40%, transparent);
}

.add-participant__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.add-participant__body {
  padding: var(--space-5) var(--space-4) var(--space-4);
}

.add-participant__title {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.add-participant__tabs {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-1);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.add-participant__tab {
  flex: 1;
  height: 36px;
  background: none;
  border: none;
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.add-participant__tab--active {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.add-participant__list {
  display: flex;
  flex-direction: column;
  max-height: 320px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.add-participant__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--color-border);
}

.add-participant__name {
  font-weight: var(--font-weight-label);
}

.add-participant__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.add-participant__error {
  color: var(--color-danger);
}
</style>
