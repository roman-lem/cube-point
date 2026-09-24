/** Вошедший пользователь, как его отдаёт /api/auth/me. */
export interface User {
  id: number
  login: string
  display_name: string
  email: string | null
  is_admin: boolean
  must_change_password: boolean
}
