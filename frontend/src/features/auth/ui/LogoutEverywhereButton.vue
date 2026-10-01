<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { AppButton, ConfirmDialog, FormError } from '@/shared/ui'
import { logoutEverywhere } from '../api/authApi'

// Ends all sessions of the account, this one too: a forgotten or stolen
// "remember me" cookie on another device stops working.
const emit = defineEmits<{ done: [] }>()

const userStore = useUserStore()
const open = ref(false)
const loading = ref(false)
const error = ref('')

function openDialog() {
  error.value = ''
  open.value = true
}

async function confirm() {
  error.value = ''
  loading.value = true
  try {
    await logoutEverywhere()
    open.value = false
    userStore.clear()
    emit('done')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось выйти'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppButton variant="secondary" @click="openDialog">Выйти на всех устройствах</AppButton>

  <ConfirmDialog
    v-model:open="open"
    title="Выйти на всех устройствах?"
    confirm-label="Выйти везде"
    :loading="loading"
    @confirm="confirm"
  >
    <p>Вход будет сброшен на всех телефонах и компьютерах, включая этот. Чтобы продолжить, войдите снова.</p>
    <FormError v-if="error" :message="error" />
  </ConfirmDialog>
</template>
