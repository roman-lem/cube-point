import { createApp } from 'vue'
import { createPinia } from 'pinia'
// Шрифты — из сборки, без сторонних доменов. Браузер скачивает только
// подмножества (латиница, кириллица), которые встречаются на странице.
import '@fontsource-variable/jetbrains-mono'
import '@fontsource-variable/manrope'
import { SITE_NAME } from '@/shared/config'
import App from './App.vue'
import { setupAuthHandlers } from './providers/auth'
import { router } from './router'
import './styles/global.css'
import './styles/page.css'

document.title = SITE_NAME

const app = createApp(App)
// Pinia подключается до роутера: первая навигация уже читает store пользователя.
app.use(createPinia())
setupAuthHandlers(router)
app.use(router)
app.mount('#app')
