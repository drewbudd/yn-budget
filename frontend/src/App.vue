<template>
  <div class="app-shell">
    <header class="top-bar">
      <div>
        <h1>yn-budget dashboard</h1>
        <p>Monthly and category spending visualizations for your home budget.</p>
      </div>
    </header>
    <main>
      <SpendingDashboard />
    </main>
  </div>
</template>

<script lang="ts">
import SpendingDashboard from './components/SpendingDashboard.vue'

export default {
  components: {
    SpendingDashboard,
  },
}
</script>

<style scoped>
.app-shell {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.5rem;
  font-family: Inter, system-ui, sans-serif;
  color: #1f2937;
}
.top-bar {
  margin-bottom: 1.5rem;
}
.top-bar h1 {
  margin: 0;
  font-size: 2rem;
}
.top-bar p {
  margin: 0.5rem 0 0;
  color: #4b5563;
}
</style>
