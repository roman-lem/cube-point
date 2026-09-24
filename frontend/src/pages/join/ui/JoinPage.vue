<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { joinMeetup } from '@/features/meetup-join'
import { ApiError } from '@/shared/api'
import { AppCard, PageHeader } from '@/shared/ui'

// Переход по ссылке или QR-коду встречи. Гость сначала входит или регистрируется
// (с баннером встречи), затем возвращается сюда, и заявка создаётся автоматически.
const { token } = defineProps<{ token: string }>()

const router = useRouter()
const userStore = useUserStore()
const error = ref('')

onMounted(async () => {
  if (!userStore.user) {
    // Сначала вход; со страницы входа можно перейти на регистрацию (ссылка сохраняет join).
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
