<template>
  <span class="live-indicator">
    <span class="live-indicator__dot" aria-hidden="true" />
    LIVE
  </span>
</template>

<style scoped>
.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  letter-spacing: 0.05em;
}

.live-indicator__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: live-pulse 1.6s ease-in-out infinite;
}

@keyframes live-pulse {
  50% {
    opacity: 0.35;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-indicator__dot {
    animation: none;
  }
}
</style>
