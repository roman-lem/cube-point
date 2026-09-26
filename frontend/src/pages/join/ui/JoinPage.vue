<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { joinMeetup } from '@/features/meetup-join'
import { ApiError } from '@/shared/api'
import { AppCard, PageHeader } from '@/shared/ui'

// Following a meetup link or QR code. A guest first logs in or registers
// (with the meetup banner), then comes back here and the request is created automatically.
const { token } = defineProps<{ token: string }>()

const router = useRouter()
const userStore = useUserStore()
const error = ref('')

onMounted(async () => {
  if (!userStore.user) {
    // Login first; the login page links to registration (the link keeps join).
    router.replace({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath, join: token },
    })
    return
  }
  try {
    const { meetup_id } = await joinMeetup(token)
    router.replace({ name: 'meetup', params: { meetupId: meetup_id } })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось подать заявку'
  }
})
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Участие во встрече" :back-to="{ name: 'home' }" />
    <AppCard v-if="error">{{ error }}</AppCard>
    <p v-else class="page__muted">Подаём заявку…</p>
  </main>
</template>
