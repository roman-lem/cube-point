<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { AppButton } from '@/shared/ui'
import { logout } from '../api/authApi'

const emit = defineEmits<{ done: [] }>()

const userStore = useUserStore()
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    await logout()
    userStore.clear()
    emit('done')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppButton variant="secondary" :loading="loading" @click="submit">Выйти</AppButton>
</template>
