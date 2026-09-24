<script setup lang="ts">
import { reactive, ref } from 'vue'
import {
  ClubLogo, LINK_NAMES, LOGO_COLORS, type Club, type LinkType, type LogoColor,
} from '@/entities/club'
import { useFormErrors } from '@/shared/lib'
import {
  AppButton, AppCard, AppIcon, AppInput, AppSelect, AppTextarea, FormError,
} from '@/shared/ui'
import { updateClub, type ClubSettings } from '../api/updateClub'

const { club } = defineProps<{ club: Club }>()
const emit = defineEmits<{ saved: [club: Club] }>()

const { fieldErrors, formError, clearErrors, showError } = useFormErrors()

const form = reactive<ClubSettings>({
  name: club.name,
  city: club.city,
  description: club.description ?? '',
  logo_color: club.logo_color,
  links: club.links.map((link) => ({ ...link })),
})

const linkTypeOptions = (Object.keys(LINK_NAMES) as LinkType[]).map((value) => ({
  value,
  label: LINK_NAMES[value],
}))

const COLOR_NAMES: Record<LogoColor, string> = {
  blue: 'Синий',
  sky: 'Голубой',
  teal: 'Бирюзовый',
  amber: 'Янтарный',
  orange: 'Оранжевый',
  rose: 'Малиновый',
  slate: 'Серый',
  brown: 'Коричневый',
}

const loading = ref(false)
const saved = ref(false)

function addLink() {
  form.links.push({ type: 'vk', url: '' })
}

function removeLink(index: number) {
  form.links.splice(index, 1)
}

async function submit() {
  clearErrors()
  saved.value = false
  loading.value = true
  try {
    emit('saved', await updateClub(club.id, form))
    saved.value = true
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="club-settings" novalidate @submit.prevent="submit">
    <AppCard class="club-settings__logo">
      <ClubLogo :name="form.name || club.name" :color="form.logo_color" :size="72" />
      <fieldset class="club-settings__colors">
        <legend class="club-settings__label">Цвет логотипа</legend>
        <label
          v-for="color in LOGO_COLORS"
          :key="color"
          class="club-settings__color"
          :style="{ background: `var(--color-logo-${color})` }"
        >
          <input
            v-model="form.logo_color"
            type="radio"
            name="logo_color"
            :value="color"
            :aria-label="COLOR_NAMES[color]"
          />
          <AppIcon v-if="form.logo_color === color" name="check" :size="18" />
        </label>
      </fieldset>
      <p v-if="fieldErrors.logo_color" class="club-settings__error">{{ fieldErrors.logo_color }}</p>
    </AppCard>

    <AppCard class="club-settings__fields">
      <AppInput v-model="form.name" label="Название" :error="fieldErrors.name" />
      <AppInput v-model="form.city" label="Город" :error="fieldErrors.city" />
      <AppTextarea v-model="form.description" label="Описание" :error="fieldErrors.description" />
    </AppCard>

    <AppCard class="club-settings__fields">
      <h2 class="club-settings__heading">Ссылки</h2>
      <p v-if="fieldErrors.links" class="club-settings__error">{{ fieldErrors.links }}</p>
      <div v-for="(link, index) in form.links" :key="index" class="club-settings__link">
        <AppSelect
          v-model="link.type"
          class="club-settings__link-type"
          :options="linkTypeOptions"
          aria-label="Тип ссылки"
          :error="fieldErrors[`links.${index}.type`]"
        />
        <AppInput
          v-model="link.url"
          class="club-settings__link-url"
          label="Адрес ссылки"
          placeholder="vk.com/club"
          :error="fieldErrors[`links.${index}.url`]"
        />
        <button
          type="button"
          class="club-settings__remove"
          aria-label="Удалить ссылку"
          @click="removeLink(index)"
        >
          <AppIcon name="delete" :size="20" />
        </button>
      </div>
      <AppButton variant="secondary" @click="addLink">
        <AppIcon name="add" :size="20" />
        Добавить ссылку
      </AppButton>
    </AppCard>

    <FormError v-if="formError" :message="formError" />
    <p v-if="saved" class="club-settings__saved" role="status">Настройки сохранены</p>
    <AppButton type="submit" class="club-settings__submit" :loading="loading">
      <AppIcon name="check" :size="20" />
      Сохранить
    </AppButton>
  </form>
</template>

<style scoped>
.club-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.club-settings__logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.club-settings__colors {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  border: none;
}

.club-settings__label {
  width: 100%;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  text-align: center;
}

.club-settings__color {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: var(--color-on-primary);
  cursor: pointer;
}

.club-settings__color:has(input:focus-visible) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.club-settings__color input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.club-settings__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.club-settings__heading {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.club-settings__link {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.club-settings__link-url {
  grid-column: 1 / -1;
  grid-row: 2;
}

/* Подпись поля ссылки есть для экранных читалок, визуально её заменяет тип. */
.club-settings__link-url :deep(label) {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}

.club-settings__remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--control-height);
  height: var(--control-height);
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.club-settings__remove:hover {
  color: var(--color-danger);
}

.club-settings__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.club-settings__saved {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}

.club-settings__submit {
  width: 100%;
}
</style>
