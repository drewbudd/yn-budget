<template>
  <div class="app-shell">
    <header class="top-bar">
      <div class="brand">
        <h1>yn-budget</h1>
        <p>A smart, elegant personal budget and finance tracker.</p>
      </div>
      <nav class="tab-navigation">
        <button 
          @click="currentTab = 'dashboard'" 
          class="tab-btn" 
          :class="{ active: currentTab === 'dashboard' }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="tab-icon"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
          Dashboard
        </button>
        <button 
          @click="currentTab = 'budgets'" 
          class="tab-btn" 
          :class="{ active: currentTab === 'budgets' }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="tab-icon"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
          Budgets
        </button>
        <button 
          @click="currentTab = 'import'" 
          class="tab-btn" 
          :class="{ active: currentTab === 'import' }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="tab-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          Import
        </button>
      </nav>
    </header>
    <main class="main-content">
      <KeepAlive>
        <component :is="currentTabComponent" />
      </KeepAlive>
    </main>
  </div>
</template>

<script lang="ts">
import { ref, computed } from 'vue'
import SpendingDashboard from './components/SpendingDashboard.vue'
import BudgetManager from './components/BudgetManager.vue'
import TransactionImporter from './components/TransactionImporter.vue'

export default {
  components: {
    SpendingDashboard,
    BudgetManager,
    TransactionImporter,
  },
  setup() {
    const currentTab = ref('dashboard')
    const currentTabComponent = computed(() => {
      if (currentTab.value === 'dashboard') return 'SpendingDashboard'
      if (currentTab.value === 'budgets') return 'BudgetManager'
      return 'TransactionImporter'
    })
    return {
      currentTab,
      currentTabComponent
    }
  }
}
</script>

<style scoped>
.app-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
  font-family: Inter, system-ui, sans-serif;
  color: #1e293b;
}

.top-bar {
  margin-bottom: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

@media(min-width: 768px) {
  .top-bar {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 1.25rem;
  }
}

.brand h1 {
  margin: 0;
  font-size: 2.25rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
}

.brand p {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.95rem;
  font-weight: 500;
}

.tab-navigation {
  display: flex;
  background: #f1f5f9;
  padding: 0.35rem;
  border-radius: 0.85rem;
  gap: 0.25rem;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.25rem;
  border-radius: 0.65rem;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  background: transparent;
  color: #64748b;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  color: #0f172a;
}

.tab-btn.active {
  background: white;
  color: #2563eb;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
}

.tab-icon {
  width: 15px;
  height: 15px;
}

.main-content {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
