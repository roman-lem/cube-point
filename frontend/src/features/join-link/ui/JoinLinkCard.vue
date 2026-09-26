<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Meetup } from '@/entities/meetup'
import { ApiError, http } from '@/shared/api'
import { downloadBlob, formatDate, qrPng } from '@/shared/lib'
import { AppButton, AppCard, AppIcon, ConfirmDialog, QrCode } from '@/shared/ui'
import { printQr } from '../lib/printQr'

// QR code and meetup link for the organizer. The token exists until the meetup is finished.
const { meetup } = defineProps<{ meetup: Meetup & { join_token: string } }>()
const emit = defineEmits<{ reissued: [token: string] }>()

const link = computed(() => `${window.location.origin}/join/${meetup.join_token}`)
const title = computed(() => `Встреча клуба, ${formatDate(meetup.date)}`)

const copied = ref(false)
const confirmOpen = ref(false)
const reissuing = ref(false)
const error = ref('')

async function copy() {
  try {
    await navigator.clipboard.writeText(link.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    error.value = 'Не удалось скопировать, выделите ссылку вручную'
  }
}

async function download() {
  downloadBlob(await qrPng(link.value), `qr-${meetup.date}.png`)
}

function print() {
  printQr(link.value, meetup.club.name, `${title.value} · отсканируйте, чтобы участвовать`)
}

async function reissue() {
  reissuing.value = true
  error.value = ''
  try {
    const { join_token } = await http.post<{ join_token: string }>(
      `/api/meetups/${meetup.id}/token`,
    )
    confirmOpen.value = false
    emit('reissued', join_token)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось перевыпустить ссылку'
  } finally {
    reissuing.value = false
  }
}
</script>

<template>
  <AppCard class="join-link">
    <div class="join-link__header">
      <AppIcon name="qr-code" />
      <div>
        <h2 class="join-link__title">QR-код встречи</h2>
        <p class="join-link__note">По нему участники подают заявку</p>
      </div>
    </div>
    <QrCode :value="link" class="join-link__qr" />
    <div class="join-link__url">
      <span class="join-link__url-text">{{ link }}</span>
      <button type="button" class="join-link__copy" aria-label="Скопировать ссылку" @click="copy">
        <AppIcon :name="copied ? 'check' : 'copy'" :size="20" />
      </button>
    </div>
    <div class="join-link__actions">
      <AppButton variant="secondary" @click="download">
        <AppIcon name="download" :size="20" />
        Скачать
      </AppButton>
      <AppButton variant="secondary" @click="print">
        <AppIcon name="print" :size="20" />
        Печать
      </AppButton>
    </div>
    <AppButton variant="secondary" @click="confirmOpen = true">
      <AppIcon name="refresh" :size="20" />
      Перевыпустить ссылку
    </AppButton>
    <p v-if="error && !confirmOpen" class="join-link__error">{{ error }}</p>

    <ConfirmDialog
      v-model:open="confirmOpen"
      title="Перевыпустить ссылку?"
      confirm-label="Перевыпустить"
      danger
      :loading="reissuing"
      @confirm="reissue"
    >
      <p>
        Старая ссылка и напечатанные QR-коды перестанут работать. Уже поданные заявки
        и подтверждённые участники останутся.
      </p>
      <p v-if="error" class="join-link__error">{{ error }}</p>
    </ConfirmDialog>
  </AppCard>
</template>

<style scoped>
.join-link {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.join-link__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-primary);
}

.join-link__title {
  color: var(--color-text-primary);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.join-link__note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.join-link__qr {
  max-width: 240px;
  margin: 0 auto;
}

.join-link__url {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-left: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.join-link__url-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.join-link__copy {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: var(--control-height);
  height: var(--control-height);
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.join-link__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.join-link__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}
</style>
