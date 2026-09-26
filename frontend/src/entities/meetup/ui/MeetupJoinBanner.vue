<script setup lang="ts">
import { formatDate } from '@/shared/lib'
import { AppIcon } from '@/shared/ui'
import type { JoinPreview } from '../model/types'

// Meetup banner on the login and registration pages when the person came via the QR code.
defineProps<{ meetup: JoinPreview }>()
</script>

<template>
  <div class="join-banner">
    <span class="join-banner__icon">
      <AppIcon name="qr-code" />
    </span>
    <div class="join-banner__text">
      <p class="join-banner__club">{{ meetup.club.name }}</p>
      <p class="join-banner__title">Встреча клуба, {{ formatDate(meetup.date) }}</p>
      <p class="join-banner__hint">Войдите, чтобы участвовать</p>
    </div>
  </div>
</template>

<style scoped>
.join-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.join-banner__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
  border-radius: var(--radius-button);
  color: var(--color-primary);
}

.join-banner__text {
  min-width: 0;
}

.join-banner__club,
.join-banner__hint {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.join-banner__title {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
  line-height: 1.3;
}

.join-banner__hint {
  font-family: var(--font-mono);
}
</style>
