<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchAdminClub, fetchAdminClubs, type AdminClub, type AdminClubSummary,
} from '@/entities/club'
import { ApiError } from '@/shared/api'
import { AppButton, AppCard, AppIcon, PageHeader } from '@/shared/ui'
import AdminClubDetails from './AdminClubDetails.vue'
import AdminClubList from './AdminClubList.vue'

// Администрирование клубов (макеты admin_clubs и admin_clubs_desk).
// На телефоне — либо список, либо открытый клуб; на широком экране —
// две панели: список слева, управление клубом справа.
const { clubId } = defineProps<{ clubId?: number }>()

const router = useRouter()
const isDesktop = useMediaQuery('(min-width: 1024px)')

const clubs = ref<AdminClubSummary[] | null>(null)
const club = ref<AdminClub | null>(null)
const listError = ref('')
const clubError = ref('')

async function loadList() {
  try {
    clubs.value = await fetchAdminClubs()
    listError.value = ''
  } catch (e) {
    listError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить клубы'
  }
}

async function loadClub(id: number | undefined) {
  club.value = null
  clubError.value = ''
  if (id === undefined) {
    return
  }
  try {
    club.value = await fetchAdminClub(id)
  } catch (e) {
    clubError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить клуб'
  }
}

onMounted(loadList)
watch(() => clubId, loadClub, { immediate: true })

function onChanged(changed: AdminClub) {
  club.value = changed
  // Число организаторов в списке.
  loadList()
}

function create() {
  router.push({ name: 'admin-club-create' })
}
</script>

<template>
  <main v-if="isDesktop" class="page page--wide">
    <PageHeader
      title="Клубы"
      subtitle="Создание клубов и назначение организаторов"
      :back-to="{ name: 'profile-settings' }"
    >
      <template #action>
        <AppButton @click="create">
          <AppIcon name="add" :size="20" />
          Создать клуб
        </AppButton>
      </template>
    </PageHeader>

    <div class="admin-clubs">
      <section class="admin-clubs__list">
        <AppCard v-if="listError">{{ listError }}</AppCard>
        <AdminClubList v-else-if="clubs" :clubs="clubs" :selected-id="clubId" />
      </section>
      <section>
        <AppCard v-if="clubError">{{ clubError }}</AppCard>
        <AdminClubDetails v-else-if="club" :club="club" @changed="onChanged" />
        <AppCard v-else-if="clubId === undefined" class="admin-clubs__placeholder">
          Выберите клуб в списке
        </AppCard>
      </section>
    </div>
  </main>

  <main v-else-if="clubId !== undefined" class="page">
    <PageHeader :title="club?.name ?? 'Клуб'" :back-to="{ name: 'admin-clubs' }" />
    <AppCard v-if="clubError">{{ clubError }}</AppCard>
    <AdminClubDetails v-else-if="club" :club="club" @changed="onChanged" />
  </main>

  <main v-else class="page">
    <PageHeader
      title="Клубы"
      :subtitle="clubs ? `Всего: ${clubs.length}` : undefined"
      :back-to="{ name: 'profile-settings' }"
    />
    <AppButton @click="create">
      <AppIcon name="add" :size="20" />
      Создать клуб
    </AppButton>
    <AppCard v-if="listError">{{ listError }}</AppCard>
    <AdminClubList v-else-if="clubs" :clubs="clubs" />
  </main>
</template>

<style scoped>
.admin-clubs {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-5);
}

.admin-clubs__placeholder {
  color: var(--color-text-secondary);
  text-align: center;
}
</style>
