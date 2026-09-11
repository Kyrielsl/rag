import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')

  function setToken(value: string) {
    token.value = value
    localStorage.setItem('token', value)
  }

  function logout() {
    token.value = ''
    localStorage.removeItem('token')
  }

  return { token, setToken, logout }
})