<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { AdminClub } from '@/entities/club'
import { ClubCreateForm } from '@/features/club-create'
import { PageHeader } from '@/shared/ui'

const router = useRouter()

function onCreated(club: AdminClub) {
  router.replace({ name: 'admin-club', params: { clubId: club.id } })
}
</script>

<template>
  <main class="page page--narrow">
    <PageHeader title="Новый клуб" :back-to="{ name: 'admin-clubs' }" />
    <ClubCreateForm @created="onCreated" />
  </main>
</template>
