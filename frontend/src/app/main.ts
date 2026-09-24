import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { setupAuthHandlers } from './providers/auth'
import { router } from './router'
import './styles/global.css'
import './styles/page.css'

const app = createApp(App)
// Pinia подключается до роутера: первая навигация уже читает store пользователя.
app.use(createPinia())
setupAuthHandlers(router)
app.use(router)
app.mount('#app')
