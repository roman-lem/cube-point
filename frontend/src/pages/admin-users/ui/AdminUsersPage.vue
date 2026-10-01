<script setup lang="ts">
import { useMediaQuery, watchDebounced } from '@vueuse/core'
import { onMounted, ref, watch } from 'vue'
import { ApiError } from '@/shared/api'
import { AppCard, PageHeader } from '@/shared/ui'
import {
  fetchAdminUser, fetchAdminUsers, type AdminUser, type AdminUserCard, type UserFilter,
} from '../api/adminUsersApi'
import AdminUserCardView from './AdminUserCard.vue'
import AdminUserList from './AdminUserList.vue'

// All users for the administrator.
// On a phone either the list or the open user; on a wide screen
// two panels: the list on the left, the user card on the right.
const { userId } = defineProps<{ userId?: number }>()

const isDesktop = useMediaQuery('(min-width: 1024px)')

const query = ref('')
const filter = ref<UserFilter>('all')
const users = ref<AdminUser[] | null>(null)
const hasMore = ref(false)
const loadingMore = ref(false)
const listError = ref('')

const user = ref<AdminUserCard | null>(null)
const userError = ref('')

async function loadList() {
  try {
    const page = await fetchAdminUsers(query.value.trim(), filter.value, 0)
    users.value = page.users
    hasMore.value = page.has_more
    listError.value = ''
  } catch (e) {
    listError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить пользователей'
  }
}

async function loadMore() {
  loadingMore.value = true
  try {
    const page = await fetchAdminUsers(query.value.trim(), filter.value, users.value!.length)
    users.value = [...users.value!, ...page.users]
    hasMore.value = page.has_more
  } catch (e) {
    listError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить пользователей'
  } finally {
    loadingMore.value = false
  }
}

async function loadUser(id: number | undefined) {
  user.value = null
  userError.value = ''
  if (id === undefined) {
    return
  }
  try {
    user.value = await fetchAdminUser(id)
  } catch (e) {
    userError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить пользователя'
  }
}

onMounted(loadList)
watchDebounced(query, loadList, { debounce: 300 })
watch(filter, loadList)
watch(() => userId, loadUser, { immediate: true })

function onChanged() {
  // Anonymization and the name revert change the name both in the card and in the list.
  loadUser(userId)
  loadList()
}
</script>

<template>
  <main v-if="isDesktop" class="page page--wide">
    <PageHeader
      title="Пользователи"
      subtitle="Все аккаунты сервиса"
      :back-to="{ name: 'profile-settings' }"
    />
    <div class="admin-users">
      <section>
        <AppCard v-if="listError">{{ listError }}</AppCard>
        <AdminUserList
          v-else-if="users"
          v-model:query="query"
          v-model:filter="filter"
          :users="users"
          :has-more="hasMore"
          :loading-more="loadingMore"
          :selected-id="userId"
          @more="loadMore"
        />
      </section>
      <section>
        <AppCard v-if="userError">{{ userError }}</AppCard>
        <AdminUserCardView v-else-if="user" :user="user" @changed="onChanged" />
        <AppCard v-else-if="userId === undefined" class="admin-users__placeholder">
          Выберите пользователя в списке
        </AppCard>
      </section>
    </div>
  </main>

  <main v-else-if="userId !== undefined" class="page">
    <PageHeader :title="user?.display_name ?? 'Пользователь'" :back-to="{ name: 'admin-users' }" />
    <AppCard v-if="userError">{{ userError }}</AppCard>
    <AdminUserCardView v-else-if="user" :user="user" @changed="onChanged" />
  </main>

  <main v-else class="page">
    <PageHeader title="Пользователи" :back-to="{ name: 'profile-settings' }" />
    <AppCard v-if="listError">{{ listError }}</AppCard>
    <AdminUserList
      v-else-if="users"
      v-model:query="query"
      v-model:filter="filter"
      :users="users"
      :has-more="hasMore"
      :loading-more="loadingMore"
      @more="loadMore"
    />
  </main>
</template>

<style scoped>
.admin-users {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-5);
}

.admin-users__placeholder {
  color: var(--color-text-secondary);
  text-align: center;
}
</style>
