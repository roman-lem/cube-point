<script setup lang="ts">
import { ref } from 'vue'
import { AppIcon } from '@/shared/ui'
import { addMove, FACES, removeLast, ROTATIONS, setModifier, type Modifier } from '../model/editing'

// FMC solution keyboard. There are no M, E, S slices.
const moves = defineModel<string[]>({ required: true })

const { disabled = false } = defineProps<{ disabled?: boolean }>()

// Wide turn toggle: stays on until switched off.
const wide = ref(false)

const MODIFIERS: Modifier[] = ["'", '2']
</script>

<template>
  <div class="fmc-keyboard" role="group" aria-label="Клавиатура решения">
    <div class="fmc-keyboard__row fmc-keyboard__row--faces">
      <button
        v-for="face in FACES"
        :key="face"
        type="button"
        class="fmc-keyboard__key fmc-keyboard__key--face"
        :disabled="disabled"
        @click="moves = addMove(moves, face, wide)"
      >
        {{ wide ? `${face}w` : face }}
      </button>
    </div>
    <div class="fmc-keyboard__row">
      <button
        v-for="modifier in MODIFIERS"
        :key="modifier"
        type="button"
        class="fmc-keyboard__key"
        :disabled="disabled || moves.length === 0"
        @click="moves = setModifier(moves, modifier)"
      >
        {{ modifier }}
      </button>
      <button
        type="button"
        :class="['fmc-keyboard__key', { 'fmc-keyboard__key--active': wide }]"
        :aria-pressed="wide"
        :disabled="disabled"
        @click="wide = !wide"
      >
        w
      </button>
      <button
        v-for="rotation in ROTATIONS"
        :key="rotation"
        type="button"
        class="fmc-keyboard__key fmc-keyboard__key--rotation"
        :disabled="disabled"
        @click="moves = addMove(moves, rotation, false)"
      >
        {{ rotation }}
      </button>
      <button
        type="button"
        class="fmc-keyboard__key"
        aria-label="Удалить ход"
        :disabled="disabled || moves.length === 0"
        @click="moves = removeLast(moves)"
      >
        <AppIcon name="backspace" :size="20" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.fmc-keyboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-border);
  border-radius: var(--radius-card);
}

.fmc-keyboard__row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: var(--space-1);
}

.fmc-keyboard__row--faces {
  grid-template-columns: repeat(6, 1fr);
}

.fmc-keyboard__key {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  padding: 0;
  border: none;
  border-radius: var(--radius-button);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: var(--font-weight-time-large);
  cursor: pointer;
  touch-action: manipulation;
  user-select: none;
}

.fmc-keyboard__key--rotation {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-time-small);
}

.fmc-keyboard__key--active {
  background: var(--color-primary);
  color: var(--color-on-primary);
}

.fmc-keyboard__key:active:not(:disabled) {
  opacity: 0.7;
}

.fmc-keyboard__key:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
