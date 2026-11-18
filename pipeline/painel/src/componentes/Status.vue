<script setup lang="ts">
// Status com ícone + texto + explicação ao passar o mouse (nunca só cor; RF12, RNF09).
import { computed } from 'vue'
import { status } from '../textos'

const props = defineProps<{ codigo: string | null | undefined; motivo?: string | null }>()
const s = computed(() => status(props.codigo))
const titulo = computed(() => [s.value.explicacao, props.motivo].filter(Boolean).join(' '))
</script>

<template>
  <span class="status" :class="s.tom" :title="titulo">
    <span class="icone" aria-hidden="true">{{ s.icone }}</span>{{ s.texto }}
  </span>
</template>
