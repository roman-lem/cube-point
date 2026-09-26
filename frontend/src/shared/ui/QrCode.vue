<script setup lang="ts">
import { computed } from 'vue'
import { qrSvg } from '../lib/qr'

// QR code of a string (usually a link) as SVG.
const { value } = defineProps<{ value: string }>()

const svg = computed(() => qrSvg(value))
</script>

<template>
  <!-- The SVG is built by uqr from value, it contains no foreign markup. -->
  <div class="qr-code" role="img" :aria-label="`QR-код: ${value}`" v-html="svg" />
</template>

<style scoped>
.qr-code {
  aspect-ratio: 1;
  width: 100%;
}

.qr-code :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
