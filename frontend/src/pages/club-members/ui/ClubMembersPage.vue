<script setup lang="ts">
import { useMediaQuery, watchDebounced } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchClub, fetchMemberCard, fetchMembers, useCurrentClubStore,
  type ClubMemberCard, type ClubMembersList, type ClubPageData, type MemberFilter,
} from '@/entities/club'
import { useUserStore } from '@/entities/user'
import { CreateMemberButton } from '@/features/participant-add'
import { MemberCard } from '@/widgets/member-card'
import { ApiError } from '@/shared/api'
import { plural } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'
import MemberList from './MemberList.vue'

// Участники клуба. Всем — список (без заблокированных). Организатору и администратору —
// управление (макеты org_club_competitors, org_competitor_edit): на телефоне либо
// список, либо карточка участника; на широком экране — две панели (org_competitor_desk).
const { clubId, userId } = defineProps<{ clubId: number; userId?: number }>()

const router = useRouter()
const userStore = useUserStore()
const clubStore = useCurrentClubStore()
const isDesktop = useMediaQuery('(min-width: 1024px)')

const club = ref<ClubPageData | null>(null)
const list = ref<ClubMembersList | null>(null)
const query = ref('')
const filter = ref<MemberFilter>('all')
const listError = ref('')

const member = ref<ClubMemberCard | null>(null)
const memberError = ref('')

const canManage = computed(() => list.value?.can_manage ?? false)
const timeZone = computed(() => club.value?.club.timezone ?? 'UTC')
const subtitle = computed(() =>
  list.value && filter.value === 'all' && !query.value
    ? plural(list.value.members.length, ['участник', 'участника', 'участников'])
    : undefined,
)

async function loadList() {
  try {
    list.value = await fetchMembers(clubId, query.value.trim(), filter.value)
    listError.value = ''
  } catch (e) {
    listError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить участников'
  }
}

async function loadMember() {
  memberError.value = ''
  if (userId === undefined) {
    member.value = null
    return
  }
  try {
    member.value = await fetchMemberCard(clubId, userId)
  } catch (e) {
    member.value = null
    memberError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить участника'
  }
}

watch(
  () => clubId,
  async (id) => {
    query.value = ''
    filter.value = 'all'
    clubStore.setClubId(id)
    fetchClub(id).then((data) => (club.value = data)).catch(() => {})
    await loadList()
  },
  { immediate: true },
)
watch(() => userId, (id, previous) => {
  // При переходе к другому участнику старая карточка не должна мелькать.
  if (id !== previous) {
    member.value = null
  }
  loadMember()
}, { immediate: true })
watch(filter, loadList)
watchDebounced(query, loadList, { debounce: 300 })

function onChanged(changed: ClubMemberCard) {
  const me = userStore.user
  // Организатор снял права с себя: управлять клубом он больше не может.
  if (me && changed.user.id === me.id && changed.role === 'member' && !me.is_admin) {
    router.push({ name: 'club', params: { clubId } })
    return
  }
  member.value = changed
  loadList()
}

function onReload() {
  loadMember()
}

function onCreated(id: number) {
  loadList()
  router.push({ name: 'club-member', params: { clubId, userId: id } })
}

const title = computed(() => (canManage.value ? 'Управление участниками' : 'Участники'))
</script>

<template>
  <main v-if="canManage && isDesktop" class="page page--wide">
    <PageHeader :title="title" :subtitle="club?.club.name" :back-to="{ name: 'club', params: { clubId } }">
      <template #action>
        <CreateMemberButton :club-id="clubId" @created="onCreated" />
      </template>
    </PageHeader>

    <div class="club-members">
      <section>
        <AppCard v-if="listError">{{ listError }}</AppCard>
        <MemberList
          v-else-if="list"
          v-model:query="query"
          v-model:filter="filter"
          :club-id="clubId"
          :members="list.members"
          :can-manage="true"
          :filter-counts="list.filter_counts"
          :selected-id="userId"
        />
      </section>
      <section>
        <AppCard v-if="memberError">{{ memberError }}</AppCard>
        <MemberCard
          v-else-if="member"
          :club-id="clubId"
          :member="member"
          :time-zone="timeZone"
          @changed="onChanged"
          @reload="onReload"
        />
        <AppCard v-else-if="userId === undefined" class="club-members__placeholder">
          Выберите участника в списке
        </AppCard>
      </section>
    </div>
  </main>

  <main v-else-if="userId !== undefined" class="page">
    <PageHeader
      :title="member?.user.display_name ?? 'Участник'"
      :back-to="{ name: 'club-members', params: { clubId } }"
    />
    <AppCard v-if="memberError">{{ memberError }}</AppCard>
    <MemberCard
      v-else-if="member"
      :club-id="clubId"
      :member="member"
      :time-zone="timeZone"
      @changed="onChanged"
      @reload="onReload"
    />
  </main>

  <main v-else class="page">
    <PageHeader :title="title" :subtitle="subtitle" :back-to="{ name: 'club', params: { clubId } }" />
    <CreateMemberButton v-if="canManage" :club-id="clubId" @created="onCreated" />
    <AppCard v-if="listError">{{ listError }}</AppCard>
    <MemberList
      v-else-if="list"
      v-model:query="query"
      v-model:filter="filter"
      :club-id="clubId"
      :members="list.members"
      :can-manage="canManage"
      :filter-counts="list.filter_counts"
    />
  </main>
</template>

<style scoped>
.club-members {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-5);
}

.club-members__placeholder {
  color: var(--color-text-secondary);
  text-align: center;
}
</style>
