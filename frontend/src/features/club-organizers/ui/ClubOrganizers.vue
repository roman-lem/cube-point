<script setup lang="ts">
import { ref } from 'vue'
import type { AdminClub, UserRef } from '@/entities/club'
import { UserRow } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { useFormErrors } from '@/shared/lib'
import { AppButton, AppCard, AppIcon, AppInput, ConfirmDialog } from '@/shared/ui'
import { addOrganizer, removeOrganizer } from '../api/organizersApi'

// Организаторы клуба в администрировании: назначение по логину и снятие.
// Снятый организатор остаётся в клубе участником, последнего снять нельзя.
const { club } = defineProps<{ club: AdminClub }>()
const emit = defineEmits<{ changed: [club: AdminClub] }>()

const login = ref('')
const adding = ref(false)
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()

const removing = ref<UserRef | null>(null)
const confirmOpen = ref(false)
const removeBusy = ref(false)
const removeError = ref('')

async function add() {
  clearErrors()
  adding.value = true
  try {
    emit('changed', await addOrganizer(club.id, login.value))
    login.value = ''
  } catch (error) {
    showError(error)
  } finally {
    adding.value = false
  }
}

function askRemove(user: UserRef) {
  removing.value = user
  removeError.value = ''
  confirmOpen.value = true
}

async function remove() {
  removeBusy.value = true
  try {
    emit('changed', await removeOrganizer(club.id, removing.value!.id))
  } catch (e) {
    removeError.value = e instanceof ApiError ? e.message : 'Не удалось снять организатора'
  } finally {
    removeBusy.value = false
    confirmOpen.value = false
  }
}
</script>

<template>
  <AppCard class="club-organizers">
    <div class="club-organizers__header">
      <h2 class="club-organizers__heading">Организаторы</h2>
      <span class="club-organizers__count">{{ club.organizers.length }}</span>
    </div>
    <p class="club-organizers__muted">
      Организаторы управляют клубом, создают встречи и вносят результаты.
    </p>

    <ul class="club-organizers__list">
      <li v-for="user in club.organizers" :key="user.id">
        <UserRow :display-name="user.display_name" :login="user.login">
          <button
            type="button"
            class="club-organizers__remove"
            :aria-label="`Снять ${user.display_name}`"
            @click="askRemove(user)"
          >
            <AppIcon name="delete" :size="20" />
          </button>
        </UserRow>
      </li>
    </ul>
    <p v-if="removeError" class="club-organizers__error" role="alert">{{ removeError }}</p>

    <form class="club-organizers__add" novalidate @submit.prevent="add">
      <AppInput
        v-model="login"
        class="club-organizers__login"
        label="Логин нового организатора"
        autocomplete="off"
        :error="fieldErrors.login || formError"
      />
      <AppButton type="submit" variant="secondary" :loading="adding">
        <AppIcon name="add" :size="20" />
        Добавить
      </AppButton>
    </form>
  </AppCard>

  <ConfirmDialog
    v-model:open="confirmOpen"
    title="Снять организатора?"
    confirm-label="Снять"
    danger
    :loading="removeBusy"
    @confirm="remove"
  >
    <p v-if="removing">
      {{ removing.display_name }} останется в клубе участником, но не сможет управлять клубом.
    </p>
  </ConfirmDialog>
</template>

<style scoped>
.club-organizers {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.club-organizers__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.club-organizers__heading {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.club-organizers__count {
  padding: 0 var(--space-2);
  background: var(--color-background);
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  font-variant-numeric: tabular-nums;
}

.club-organizers__muted {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.club-organizers__list {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.club-organizers__list li + li {
  border-top: 1px solid var(--color-border);
}

.club-organizers__remove {
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

.club-organizers__remove:hover {
  color: var(--color-danger);
}

.club-organizers__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.club-organizers__add {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

@media (min-width: 640px) {
  .club-organizers__add {
    flex-direction: row;
    align-items: flex-start;
  }

  .club-organizers__login {
    flex: 1;
  }

  /* Кнопка на одной линии с полем, а не с подписью над ним. */
  .club-organizers__add > :last-child {
    margin-top: calc(var(--font-size-label) * 1.5 + var(--space-2));
  }
}
</style>
