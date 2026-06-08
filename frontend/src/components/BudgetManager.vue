<template>
  <section class="budget-manager">
    <!-- Top Selector and Global Status Card -->
    <div class="header-card">
      <div class="date-nav-wrapper">
        <button 
          @click="navigateMonth(-1)" 
          class="nav-arrow-btn" 
          title="Previous Month"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>

        <div class="selectors">
          <label class="select-label">
            Year
            <select v-model.number="selectedYear" @change="fetchBudgets" class="form-select">
              <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
            </select>
          </label>
          <label class="select-label">
            Month
            <select v-model.number="selectedMonth" @change="fetchBudgets" class="form-select">
              <option v-for="m in 12" :key="m" :value="m">{{ getMonthName(m) }}</option>
            </select>
          </label>
        </div>

        <button 
          @click="navigateMonth(1)" 
          class="nav-arrow-btn" 
          title="Next Month"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
        </button>

        <button 
          @click="jumpToCurrentMonth" 
          class="btn btn-secondary btn-today" 
          :disabled="isCurrentMonthActive"
          title="Jump to Current Month"
        >
          Today
        </button>
      </div>

      <div class="global-summary">
        <div class="stat">
          <span class="label">Total Budgeted</span>
          <span class="value">{{ formatCurrency(totalBudgeted) }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat">
          <span class="label">Total Spent</span>
          <span class="value">{{ formatCurrency(totalActualSpent) }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat" :class="globalStatusClass">
          <span class="label">{{ totalRemaining >= 0 ? 'Total Remaining' : 'Total Over budget' }}</span>
          <span class="value">{{ formatCurrency(Math.abs(totalRemaining)) }}</span>
        </div>
      </div>
    </div>

    <!-- Actions Bar -->
    <div class="actions-bar">
      <div class="copy-tool-wrapper">
        <span class="copy-tool-label">Copy budget from:</span>
        <div class="copy-selectors">
          <select v-model.number="copyYear" class="form-select form-select-sm">
            <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
          </select>
          <select v-model.number="copyMonth" class="form-select form-select-sm">
            <option v-for="m in 12" :key="m" :value="m">{{ getMonthName(m) }}</option>
          </select>
          <button @click="copySpecificBudget" class="btn btn-secondary btn-sm btn-icon" title="Copy from selected month">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            Copy
          </button>
        </div>
      </div>

      <div class="right-actions">
        <span v-if="toastMessage" class="toast-alert" :class="toastClass">
          {{ toastMessage }}
        </span>
        <button @click="saveBudget" class="btn btn-primary" :disabled="isSaving">
          <span v-if="isSaving" class="spinner"></span>
          {{ isSaving ? 'Saving...' : 'Save Budget' }}
        </button>
      </div>
    </div>

    <!-- Category Budget List -->
    <div class="budget-list">
      <div v-if="loading" class="loading-state">
        <div class="spinner large"></div>
        <p>Loading budget configurations...</p>
      </div>

      <div v-else-if="budgets.length === 0" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
        <h3>No transaction categories found</h3>
        <p>Please import some transactions in the CSV uploader first to get started.</p>
      </div>

      <div v-else class="cards-grid">
        <div v-for="item in budgets" :key="item.category" class="budget-card" :class="getCardStatusClass(item)">
          <div class="card-header">
            <h3 class="category-name">{{ item.category }}</h3>
            <div class="budget-input-wrapper">
              <span class="currency-prefix">€</span>
              <input 
                type="number" 
                min="0" 
                step="5"
                placeholder="0.00"
                v-model.number="item.budget" 
                class="budget-input"
              />
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-labels">
              <span class="actual-spent">Spent: <strong>{{ formatCurrency(item.actual) }}</strong></span>
              <span class="percent-label" v-if="item.budget > 0">
                {{ getPercentage(item.actual, item.budget) }}%
              </span>
            </div>
            <div class="progress-track">
              <div 
                class="progress-fill" 
                :style="{ width: Math.min(100, getPercentageRaw(item.actual, item.budget)) + '%' }"
                :class="getProgressColorClass(item.actual, item.budget)"
              ></div>
            </div>
          </div>

          <div class="card-footer">
            <span class="remaining-value" :class="getRemainingColorClass(item)">
              <template v-if="item.budget === 0">
                No budget defined
              </template>
              <template v-else-if="item.budget >= item.actual">
                {{ formatCurrency(item.budget - item.actual) }} remaining
              </template>
              <template v-else>
                {{ formatCurrency(item.actual - item.budget) }} over budget
              </template>
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { ref, onMounted, computed, watch } from 'vue'

interface BudgetCategory {
  category: string
  budget: number
  actual: number
}

export default {
  setup() {
    const selectedYear = ref(new Date().getFullYear())
    const selectedMonth = ref(new Date().getMonth() + 1)
    const availableYears = ref<number[]>([new Date().getFullYear()])
    const budgets = ref<BudgetCategory[]>([])
    const loading = ref(false)
    const isSaving = ref(false)
    const toastMessage = ref('')
    const toastClass = ref('')

    // Copy parameters
    const copyYear = ref(new Date().getFullYear())
    const copyMonth = ref(new Date().getMonth() + 1)

    const currentRealYear = new Date().getFullYear()
    const currentRealMonth = new Date().getMonth() + 1

    const formatCurrency = (val: number) => {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'EUR'
      }).format(val)
    }

    const getMonthName = (m: number) => {
      const date = new Date(2000, m - 1, 1)
      return date.toLocaleString('default', { month: 'long' })
    }

    const getPercentageRaw = (actual: number, budget: number) => {
      if (!budget) return 0
      return (actual / budget) * 100
    }

    const getPercentage = (actual: number, budget: number) => {
      return Math.round(getPercentageRaw(actual, budget))
    }

    const totalBudgeted = computed(() => {
      return budgets.value.reduce((sum, b) => sum + (b.budget || 0), 0)
    })

    const totalActualSpent = computed(() => {
      return budgets.value.reduce((sum, b) => sum + (b.actual || 0), 0)
    })

    const totalRemaining = computed(() => {
      return totalBudgeted.value - totalActualSpent.value
    })

    const globalStatusClass = computed(() => {
      if (totalRemaining.value < 0) return 'status-danger'
      if (totalRemaining.value < totalBudgeted.value * 0.15) return 'status-warning'
      return 'status-success'
    })

    const getProgressColorClass = (actual: number, budget: number) => {
      if (!budget) return 'bg-neutral'
      const pct = (actual / budget) * 100
      if (pct > 100) return 'bg-danger'
      if (pct >= 75) return 'bg-warning'
      return 'bg-success'
    }

    const getCardStatusClass = (item: BudgetCategory) => {
      if (!item.budget) return ''
      const pct = (item.actual / item.budget) * 100
      if (pct > 100) return 'card-danger'
      if (pct >= 75) return 'card-warning'
      return ''
    }

    const getRemainingColorClass = (item: BudgetCategory) => {
      if (!item.budget) return 'text-neutral'
      if (item.actual > item.budget) return 'text-danger'
      if (item.actual >= item.budget * 0.75) return 'text-warning'
      return 'text-success'
    }

    const showToast = (message: string, isError = false) => {
      toastMessage.value = message
      toastClass.value = isError ? 'alert-danger' : 'alert-success'
      setTimeout(() => {
        toastMessage.value = ''
      }, 4000)
    }

    const getCsrfToken = (): string => {
      const name = 'csrftoken'
      const cookieValue = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)')
      return cookieValue ? cookieValue.pop() || '' : ''
    }

    const fetchBudgets = async () => {
      loading.value = true
      try {
        const response = await fetch(`/api/budgets/?year=${selectedYear.value}&month=${selectedMonth.value}`)
        if (!response.ok) throw new Error('Failed to load budgets')
        const data = await response.json()
        budgets.value = data.budgets
      } catch (err) {
        showToast('Error loading budgets', true)
      } finally {
        loading.value = false
      }
    }

    const saveBudget = async () => {
      isSaving.value = true
      try {
        const budgetMap: Record<string, number> = {}
        budgets.value.forEach(b => {
          budgetMap[b.category] = b.budget || 0
        })

        const response = await fetch('/api/budgets/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            year: selectedYear.value,
            month: selectedMonth.value,
            budgets: budgetMap
          })
        })

        if (!response.ok) throw new Error('Failed to save')
        showToast('Budget saved successfully!')
        await fetchBudgets()
      } catch (err) {
        showToast('Error saving budget configurations', true)
      } finally {
        isSaving.value = false
      }
    }

    // Dynamic copy target prefilling (defaults to previous month)
    watch([selectedYear, selectedMonth], () => {
      let prevMonth = selectedMonth.value - 1
      let prevYear = selectedYear.value
      if (prevMonth === 0) {
        prevMonth = 12
        prevYear -= 1
      }
      copyMonth.value = prevMonth
      copyYear.value = prevYear
    }, { immediate: true })

    const copySpecificBudget = async () => {
      try {
        const response = await fetch(`/api/budgets/?year=${copyYear.value}&month=${copyMonth.value}`)
        if (!response.ok) throw new Error()
        const data = await response.json()
        const copiedBudgets = data.budgets as BudgetCategory[]
        if (copiedBudgets.length === 0 || copiedBudgets.every(b => !b.budget)) {
          showToast(`No budget found for ${getMonthName(copyMonth.value)} ${copyYear.value}`, true)
          return
        }

        const copiedMap = new Map(copiedBudgets.map(b => [b.category, b.budget]))
        budgets.value = budgets.value.map(b => ({
          ...b,
          budget: copiedMap.get(b.category) || 0
        }))
        showToast(`Copied budget configuration from ${getMonthName(copyMonth.value)} ${copyYear.value}. Click "Save Budget" to save.`)
      } catch (err) {
        showToast('Could not fetch selected month\'s budget', true)
      }
    }

    // Left/Right arrow navigation
    const navigateMonth = (direction: number) => {
      let m = selectedMonth.value + direction
      let y = selectedYear.value
      if (m === 0) {
        m = 12
        y -= 1
      } else if (m === 13) {
        m = 1
        y += 1
      }

      if (!availableYears.value.includes(y)) {
        availableYears.value.push(y)
        availableYears.value.sort((a, b) => b - a)
      }

      selectedMonth.value = m
      selectedYear.value = y
      fetchBudgets()
    }

    // Jump to Today
    const jumpToCurrentMonth = () => {
      selectedYear.value = currentRealYear
      selectedMonth.value = currentRealMonth
      fetchBudgets()
    }

    const isCurrentMonthActive = computed(() => {
      return selectedYear.value === currentRealYear && selectedMonth.value === currentRealMonth
    })

    const fetchAvailableYears = async () => {
      try {
        const response = await fetch('/stats/')
        if (!response.ok) return
        const data = await response.json()
        const yearsSet = new Set<number>()
        data.monthly_totals.forEach((row: any) => yearsSet.add(row.year))
        yearsSet.add(new Date().getFullYear())
        availableYears.value = Array.from(yearsSet).sort((a, b) => b - a)
      } catch (err) {
        // Fallback
      }
    }

    onMounted(async () => {
      await fetchAvailableYears()
      await fetchBudgets()
    })

    return {
      selectedYear,
      selectedMonth,
      availableYears,
      budgets,
      loading,
      isSaving,
      toastMessage,
      toastClass,
      totalBudgeted,
      totalActualSpent,
      totalRemaining,
      globalStatusClass,
      copyYear,
      copyMonth,
      isCurrentMonthActive,
      formatCurrency,
      getMonthName,
      getPercentageRaw,
      getPercentage,
      getProgressColorClass,
      getCardStatusClass,
      getRemainingColorClass,
      fetchBudgets,
      saveBudget,
      copySpecificBudget,
      navigateMonth,
      jumpToCurrentMonth
    }
  }
}
</script>

<style scoped>
.budget-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  font-family: Inter, system-ui, sans-serif;
}

.header-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1.25rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media(min-width: 768px) {
  .header-card {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.date-nav-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.nav-arrow-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 0.75rem;
  background: #f1f5f9;
  border: none;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-arrow-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
  transform: scale(1.05);
}

.nav-arrow-btn:active {
  transform: scale(0.95);
}

.btn-today {
  height: 38px;
  padding: 0 1rem;
}

.selectors {
  display: flex;
  gap: 0.75rem;
}

.select-label {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

.form-select {
  padding: 0.4rem 0.75rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 0.65rem;
  background-color: #f9fafb;
  font-weight: 600;
  color: #1f2937;
  outline: none;
  min-width: 100px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.form-select:focus {
  border-color: #2563eb;
  background-color: white;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.global-summary {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  background: #f8fafc;
  padding: 0.85rem 1.5rem;
  border-radius: 1rem;
  border: 1px solid #f1f5f9;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stat .label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  font-weight: 600;
}

.stat .value {
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: #e2e8f0;
}

.status-success .value {
  color: #16a34a;
}

.status-warning .value {
  color: #d97706;
}

.status-danger .value {
  color: #dc2626;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.copy-tool-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: white;
  padding: 0.5rem 1rem;
  border-radius: 0.85rem;
  border: 1.5px solid #e2e8f0;
}

.copy-tool-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.copy-selectors {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-select-sm {
  padding: 0.35rem 0.65rem;
  min-width: 90px;
  font-size: 0.8rem;
  border-radius: 0.5rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 1.25rem;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-sm {
  padding: 0.4rem 0.85rem;
  font-size: 0.8rem;
  border-radius: 0.5rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.15);
}

.btn-secondary {
  background: white;
  color: #4b5563;
  border: 1.5px solid #e5e7eb;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.toast-alert {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.85rem;
  font-weight: 500;
  animation: fadeIn 0.3s ease;
}

.alert-success {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.alert-danger {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.25rem;
}

.budget-card {
  background: white;
  padding: 1.25rem;
  border-radius: 1.25rem;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: all 0.2s ease;
}

.budget-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.04);
}

.budget-card.card-warning {
  border-left: 4px solid #f59e0b;
}

.budget-card.card-danger {
  border-left: 4px solid #ef4444;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
}

.budget-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.currency-prefix {
  position: absolute;
  left: 0.65rem;
  color: #94a3b8;
  font-size: 0.9rem;
  font-weight: 600;
}

.budget-input {
  width: 95px;
  padding: 0.4rem 0.5rem 0.4rem 1.4rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 0.6rem;
  font-weight: 600;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s;
  text-align: right;
  -moz-appearance: textfield;
}

.budget-input::-webkit-outer-spin-button,
.budget-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.budget-input:focus {
  border-color: #2563eb;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #64748b;
}

.percent-label {
  font-weight: 700;
}

.progress-track {
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease-out;
}

.bg-success { background-color: #22c55e; }
.bg-warning { background-color: #eab308; }
.bg-danger { background-color: #ef4444; }
.bg-neutral { background-color: #cbd5e1; }

.card-footer {
  margin-top: auto;
  font-size: 0.85rem;
  font-weight: 600;
}

.text-success { color: #16a34a; }
.text-warning { color: #d97706; }
.text-danger { color: #dc2626; }
.text-neutral { color: #64748b; }

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
  background: white;
  border-radius: 1.25rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.empty-state svg {
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem;
  color: #1f2937;
}

.empty-state p {
  margin: 0;
  color: #6b7280;
  font-size: 0.95rem;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.large {
  width: 32px;
  height: 32px;
  border: 3px solid #f1f5f9;
  border-top-color: #2563eb;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
