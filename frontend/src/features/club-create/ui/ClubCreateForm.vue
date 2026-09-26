<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { reactive, ref } from 'vue'
import type { AdminClub, UserRef } from '@/entities/club'
import { UserRow } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { DEFAULT_TIME_ZONE, timeZoneOptions, useFormErrors } from '@/shared/lib'
import { AppButton, AppCard, AppIcon, AppInput, AppSelect, FormError } from '@/shared/ui'
import { createClub, searchUsers } from '../api/createClub'

// Club creation by the administrator: name, city,
// time zone and a required first organizer found by login.
const emit = defineEmits<{ created: [club: AdminClub] }>()

const { fieldErrors, formError, clearErrors, showError } = useFormErrors()

const form = reactive({ name: '', city: '', timezone: DEFAULT_TIME_ZONE })
const timeZones = timeZoneOptions()

const query = ref('')
const found = ref<UserRef[]>([])
const searchError = ref('')
const organizer = ref<UserRef | null>(null)
const loading = ref(false)

watchDebounced(
  query,
  async (text) => {
    searchError.value = ''
    if (!text.trim()) {
      found.value = []
      return
    }
    try {
      found.value = await searchUsers(text.trim())
    } catch (e) {
      searchError.value = e instanceof ApiError ? e.message : 'Не удалось найти пользователей'
    }
  },
  { debounce: 300 },
)

function select(user: UserRef) {
  organizer.value = user
  query.value = ''
  found.value = []
}

async function submit() {
  clearErrors()
  loading.value = true
  try {
    emit('created', await createClub({ ...form, organizer_login: organizer.value?.login ?? '' }))
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="club-create" novalidate @submit.prevent="submit">
    <AppCard class="club-create__card">
      <AppInput v-model="form.name" label="Название" autocomplete="off" :error="fieldErrors.name" />
      <AppInput v-model="form.city" label="Город" autocomplete="off" :error="fieldErrors.city" />
      <AppSelect
        v-model="form.timezone"
        label="Часовой пояс"
        :options="timeZones"
        :error="fieldErrors.timezone"
      />
    </AppCard>

    <AppCard class="club-create__card">
      <div>
        <h2 class="club-create__heading">Первый организатор</h2>
        <p class="club-create__muted">
          Каждому клубу нужен хотя бы один организатор, чтобы создавать встречи и вносить результаты.
        </p>
      </div>

      <UserRow v-if="organizer" :display-name="organizer.display_name" :login="organizer.login">
        <span class="club-create__selected">
          <AppIcon name="check" :size="18" />
          Выбран
        </span>
        <button
          type="button"
          class="club-create__clear"
          aria-label="Выбрать другого"
          @click="organizer = null"
        >
          <AppIcon name="close" :size="20" />
        </button>
      </UserRow>

      <template v-else>
        <AppInput
          v-model="query"
          label="Логин"
          placeholder="Поиск по логину"
          autocomplete="off"
          :error="fieldErrors.organizer_login || searchError"
        />
        <ul v-if="found.length" class="club-create__found">
          <li v-for="user in found" :key="user.id">
            <UserRow :display-name="user.display_name" :login="user.login">
              <AppButton variant="secondary" @click="select(user)">Выбрать</AppButton>
            </UserRow>
          </li>
        </ul>
        <p v-else-if="query.trim()" class="club-create__muted">Никого не нашли</p>
      </template>
    </AppCard>

    <p class="club-create__muted">
      Описание, логотип и ссылки организатор заполнит сам в настройках клуба.
    </p>
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" :loading="loading">Создать</AppButton>
  </form>
</template>

<style scoped>
.club-create,
.club-create__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.club-create__heading {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.club-create__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.club-create__selected {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.club-create__clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--control-height);
  height: var(--control-height);
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.club-create__found {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.club-create__found li + li {
  border-top: 1px solid var(--color-border);
}
</style>
