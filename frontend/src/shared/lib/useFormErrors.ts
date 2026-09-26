import { ref } from 'vue'
import { ApiError, type FieldErrors } from '@/shared/api'

/** Form errors: under the fields (fieldErrors) and a general one above the button (formError). */
export function useFormErrors() {
  const fieldErrors = ref<FieldErrors>({})
  const formError = ref('')

  function clearErrors() {
    fieldErrors.value = {}
    formError.value = ''
  }

  function showError(error: unknown) {
    if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
      fieldErrors.value = error.fields
    } else if (error instanceof ApiError) {
      formError.value = error.message
    } else {
      console.error(error)
      formError.value = 'Что-то пошло не так, попробуйте ещё раз'
    }
  }

  return { fieldErrors, formError, clearErrors, showError }
}
