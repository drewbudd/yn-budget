<template>
  <section class="transaction-manager">
    <!-- Status Toast Alert -->
    <div v-if="toastMessage" class="toast-alert" :class="toastClass">
      {{ toastMessage }}
    </div>

    <!-- Header Section with Selectors -->
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
            <select v-model.number="selectedYear" @change="fetchTransactions" class="form-select">
              <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
            </select>
          </label>
          <label class="select-label">
            Month
            <select v-model.number="selectedMonth" @change="fetchTransactions" class="form-select">
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

      <!-- Quick Metrics Summary -->
      <div class="global-summary">
        <div class="stat">
          <span class="label">Transactions</span>
          <span class="value">{{ filteredTransactions.length }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat">
          <span class="label">Total Amount</span>
          <span class="value" :class="totalAmount >= 0 ? 'text-success' : 'text-danger'">
            {{ formatCurrency(totalAmount) }}
          </span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat" :class="{ 'status-danger': flaggedCount > 0 }">
          <span class="label">Flagged</span>
          <span class="value">{{ flaggedCount }}</span>
        </div>
      </div>
    </div>

    <!-- Filter and Search Controls -->
    <div class="controls-bar">
      <div class="search-wrapper">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input 
          type="text" 
          v-model="searchQuery" 
          @input="debounceSearch"
          placeholder="Search partner, reference, or category..." 
          class="search-input" 
        />
      </div>

      <div class="filter-actions">
        <label class="checkbox-label">
          <input type="checkbox" v-model="showOnlyFlagged" />
          <span>Show Flagged Only</span>
        </label>
      </div>
    </div>

    <!-- Transactions List Card -->
    <div class="table-card">
      <div v-if="loading && transactions.length === 0" class="loading-state">
        <div class="spinner large"></div>
        <p>Loading transactions...</p>
      </div>

      <div v-else-if="transactions.length === 0" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
        <h3>No transactions found</h3>
        <p>There are no transactions recorded for {{ getMonthName(selectedMonth) }} {{ selectedYear }}.</p>
      </div>

      <div v-else class="table-responsive">
        <div v-if="loading" class="table-loading-overlay">
          <div class="spinner large"></div>
        </div>
        <table class="manager-table">
          <thead>
            <tr>
              <th width="35" class="text-center">Flag</th>
              <th>Date</th>
              <th>Partner</th>
              <th>Category</th>
              <th class="text-right">Amount</th>
              <th>Type / Reference</th>
              <th class="text-center" width="140">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="t in filteredTransactions" 
              :key="t.id"
              :class="{ 'row-flagged': t.is_flagged, 'row-editing': editingId === t.id }"
            >
              <!-- Flag Toggle Column -->
              <td class="text-center">
                <button 
                  @click="toggleFlag(t)" 
                  class="btn-flag" 
                  :class="{ flagged: t.is_flagged }" 
                  title="Toggle Flag for Review"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" class="flag-icon">
                    <path d="M4 2v20h-2v-20h2zm18 4l-4 4 4 4h-14v-8h14z"/>
                  </svg>
                </button>
              </td>

              <!-- Date Column -->
              <td>
                <template v-if="editingId === t.id">
                  <input type="date" v-model="editForm.booking_date" class="form-input form-input-sm" />
                </template>
                <template v-else>
                  <span class="whitespace-nowrap">{{ formatDate(t.booking_date) }}</span>
                </template>
              </td>

              <!-- Partner Column -->
              <td class="partner-cell" :title="t.partner_name">
                {{ t.partner_name || '-' }}
              </td>

              <!-- Category Column -->
              <td>
                <template v-if="editingId === t.id">
                  <select v-model="editForm.category" class="table-select">
                    <option value="">Uncategorized</option>
                    <option v-for="opt in categoryChoices" :key="opt" :value="opt">
                      {{ opt }}
                    </option>
                  </select>
                </template>
                <template v-else>
                  <span class="badge badge-light">{{ t.category }}</span>
                </template>
              </td>

              <!-- Amount Column -->
              <td class="amount-cell text-right" :class="t.amount_eur.startsWith('-') ? 'negative' : 'positive'">
                <template v-if="editingId === t.id">
                  <input 
                    type="number" 
                    step="0.01" 
                    v-model.number="editForm.amount_eur" 
                    class="form-input form-input-sm text-right inline-amount-input" 
                  />
                </template>
                <template v-else>
                  {{ formatCurrency(parseFloat(t.amount_eur)) }}
                </template>
              </td>

              <!-- Type / Reference Column -->
              <td class="reference-cell">
                <div class="transaction-type">{{ t.transaction_type }}</div>
                <div class="payment-ref" :title="t.payment_reference">{{ t.payment_reference || '-' }}</div>
              </td>

              <!-- Actions Column -->
              <td class="text-center">
                <template v-if="editingId === t.id">
                  <div class="action-buttons-group">
                    <button @click="saveEdit" class="btn-action btn-save" title="Save changes">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                    </button>
                    <button @click="cancelEdit" class="btn-action btn-cancel" title="Cancel changes">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                  </div>
                </template>
                <template v-else>
                  <div class="action-buttons-group">
                    <button @click="startEdit(t)" class="btn-action btn-edit" title="Edit entry">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                    </button>

                    <!-- Safe double-click or stateful confirm delete button -->
                    <button 
                      v-if="deletingId !== t.id" 
                      @click="requestDelete(t.id)" 
                      class="btn-action btn-delete" 
                      title="Delete entry"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                    </button>
                    <button 
                      v-else 
                      @click="confirmDelete(t.id)" 
                      class="btn-confirm-delete" 
                      title="Click again to confirm delete"
                      @mouseleave="cancelDelete"
                    >
                      Confirm?
                    </button>
                  </div>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { ref, onMounted, computed, watch } from 'vue'

interface Transaction {
  id: number
  booking_date: string
  value_date: string | null
  partner_name: string
  category: string
  amount_eur: string
  payment_reference: string
  partner_iban: string
  transaction_type: string
  account_name: string
  is_flagged: boolean
}

export default {
  setup() {
    const selectedYear = ref(new Date().getFullYear())
    const selectedMonth = ref(new Date().getMonth() + 1)
    const availableYears = ref<number[]>([new Date().getFullYear()])
    const transactions = ref<Transaction[]>([])
    const categoryChoices = ref<string[]>([])
    
    // UI states
    const loading = ref(false)
    const toastMessage = ref('')
    const toastClass = ref('')
    const searchQuery = ref('')
    const searchDebounce = ref<number | null>(null)
    const showOnlyFlagged = ref(false)

    // Inline Editing states
    const editingId = ref<number | null>(null)
    const editForm = ref({
      booking_date: '',
      category: '',
      amount_eur: 0
    })

    // Deleting states
    const deletingId = ref<number | null>(null)

    const currentRealYear = new Date().getFullYear()
    const currentRealMonth = new Date().getMonth() + 1

    const formatCurrency = (val: number) => {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'EUR'
      }).format(val)
    }

    const formatDate = (isoString: string) => {
      if (!isoString) return '-'
      const date = new Date(isoString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const getMonthName = (m: number) => {
      const date = new Date(2000, m - 1, 1)
      return date.toLocaleString('default', { month: 'long' })
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

    // Load transactions from API
    const fetchTransactions = async () => {
      loading.value = true
      try {
        const queryParams = new URLSearchParams({
          year: selectedYear.value.toString(),
          month: selectedMonth.value.toString(),
          show_flagged: showOnlyFlagged.value.toString(),
          search: searchQuery.value
        })

        const response = await fetch(`/api/transactions/?${queryParams}`)
        if (!response.ok) throw new Error()
        const data = await response.json()
        transactions.value = data.transactions
        categoryChoices.value = data.category_choices
      } catch (err) {
        showToast('Error loading transactions list', true)
      } finally {
        loading.value = false
      }
    }

    // Toggle Flag state instantly on the server
    const toggleFlag = async (t: Transaction) => {
      const targetState = !t.is_flagged
      // Optimistic UI update
      t.is_flagged = targetState

      try {
        const response = await fetch(`/api/transactions/${t.id}/update/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            is_flagged: targetState
          })
        })

        if (!response.ok) throw new Error()
        const data = await response.json()
        // Sync back with final server values just in case
        t.is_flagged = data.transaction.is_flagged
        showToast(targetState ? 'Transaction flagged for review' : 'Removed transaction flag')
      } catch (err) {
        // Rollback UI update
        t.is_flagged = !targetState
        showToast('Failed to update flag status', true)
      }
    }

    // Start inline editing
    const startEdit = (t: Transaction) => {
      editingId.value = t.id
      editForm.value = {
        booking_date: t.booking_date,
        category: t.category === 'Uncategorized' ? '' : t.category,
        amount_eur: parseFloat(t.amount_eur)
      }
    }

    const cancelEdit = () => {
      editingId.value = null
    }

    // Save inline edit
    const saveEdit = async () => {
      if (!editForm.value.booking_date) {
        showToast('Date is required', true)
        return
      }
      if (isNaN(editForm.value.amount_eur)) {
        showToast('Valid amount is required', true)
        return
      }

      try {
        const response = await fetch(`/api/transactions/${editingId.value}/update/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            booking_date: editForm.value.booking_date,
            category: editForm.value.category,
            amount_eur: editForm.value.amount_eur.toString()
          })
        })

        if (!response.ok) throw new Error()
        
        showToast('Transaction updated successfully')
        editingId.value = null
        await fetchTransactions()
      } catch (err) {
        showToast('Failed to save changes', true)
      }
    }

    // Delete actions
    const requestDelete = (id: number) => {
      deletingId.value = id
    }

    const cancelDelete = () => {
      deletingId.value = null
    }

    const confirmDelete = async (id: number) => {
      try {
        const response = await fetch(`/api/transactions/${id}/delete/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken()
          }
        })

        if (!response.ok) throw new Error()
        showToast('Transaction deleted successfully')
        deletingId.value = null
        await fetchTransactions()
      } catch (err) {
        showToast('Failed to delete transaction', true)
      }
    }

    // Month Selector actions
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
      fetchTransactions()
    }

    const jumpToCurrentMonth = () => {
      selectedYear.value = currentRealYear
      selectedMonth.value = currentRealMonth
      fetchTransactions()
    }

    const isCurrentMonthActive = computed(() => {
      return selectedYear.value === currentRealYear && selectedMonth.value === currentRealMonth
    })

    // Debounced search to avoid spamming requests while typing
    const debounceSearch = () => {
      if (searchDebounce.value) clearTimeout(searchDebounce.value)
      searchDebounce.value = window.setTimeout(() => {
        fetchTransactions()
      }, 350)
    }

    // Metrics computation
    const totalAmount = computed(() => {
      return transactions.value.reduce((sum, t) => sum + parseFloat(t.amount_eur), 0)
    })

    const flaggedCount = computed(() => {
      return transactions.value.filter(t => t.is_flagged).length
    })

    const filteredTransactions = computed(() => {
      // Backend filters show_flagged and search query, so we can return directly
      return transactions.value
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

    watch(showOnlyFlagged, () => {
      fetchTransactions()
    })

    onMounted(async () => {
      await fetchAvailableYears()
      await fetchTransactions()
    })

    return {
      selectedYear,
      selectedMonth,
      availableYears,
      transactions,
      categoryChoices,
      loading,
      toastMessage,
      toastClass,
      searchQuery,
      showOnlyFlagged,
      editingId,
      editForm,
      deletingId,
      isCurrentMonthActive,
      formatCurrency,
      formatDate,
      getMonthName,
      navigateMonth,
      jumpToCurrentMonth,
      debounceSearch,
      toggleFlag,
      startEdit,
      cancelEdit,
      saveEdit,
      requestDelete,
      cancelDelete,
      confirmDelete,
      totalAmount,
      flaggedCount,
      filteredTransactions
    }
  }
}
</script>

<style scoped>
.transaction-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  font-family: Inter, system-ui, sans-serif;
  position: relative;
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

.status-danger .value {
  color: #ef4444;
}

/* Controls / Filters bar */
.controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 480px;
  min-width: 280px;
}

.search-icon {
  position: absolute;
  left: 0.85rem;
}

.search-input {
  width: 100%;
  padding: 0.65rem 1rem 0.65rem 2.25rem;
  border: 1.5px solid #cbd5e1;
  border-radius: 0.85rem;
  outline: none;
  font-size: 0.9rem;
  font-weight: 500;
  color: #1e293b;
  transition: all 0.2s ease;
  background-color: white;
}

.search-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
}

.checkbox-label input[type=checkbox] {
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
  cursor: pointer;
}

/* Table layout styling */
.table-card {
  background: white;
  border-radius: 1.25rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
  position: relative;
}

.table-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(1px);
}

.manager-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.9rem;
}

.manager-table th {
  background: #f8fafc;
  padding: 0.85rem 1rem;
  font-weight: 700;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.manager-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}

.manager-table tr:last-child td {
  border-bottom: none;
}

.manager-table tr.row-flagged {
  background: #fffbfa;
}

.manager-table tr.row-flagged td {
  border-bottom-color: #fde8e8;
}

.manager-table tr.row-editing {
  background: #eff6ff;
}

/* Flag button styling */
.btn-flag {
  background: transparent;
  border: none;
  color: #cbd5e1;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.35rem;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-flag:hover {
  color: #94a3b8;
}

.btn-flag.flagged {
  color: #ef4444;
}

/* Text inputs and Select fields inside table */
.form-input {
  width: 100%;
  padding: 0.35rem 0.5rem;
  border: 1.5px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 0.85rem;
  outline: none;
  font-weight: 600;
  color: #0f172a;
}

.form-input:focus {
  border-color: #2563eb;
}

.form-input-sm {
  padding: 0.25rem 0.4rem;
}

.inline-amount-input {
  max-width: 100px;
}

.table-select {
  padding: 0.35rem 0.5rem;
  border: 1.5px solid #cbd5e1;
  border-radius: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  outline: none;
  background-color: white;
  color: #1e293b;
  cursor: pointer;
  width: 100%;
  max-width: 160px;
}

.table-select:focus {
  border-color: #2563eb;
}

/* Cell types styling */
.partner-cell {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: #1e293b;
}

.reference-cell {
  max-width: 240px;
}

.transaction-type {
  font-size: 0.75rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
}

.payment-ref {
  font-size: 0.8rem;
  color: #475569;
  margin-top: 0.15rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.amount-cell {
  font-weight: 700;
  white-space: nowrap;
}

.amount-cell.negative {
  color: #dc2626;
}

.amount-cell.positive {
  color: #16a34a;
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
}

.badge-light {
  background-color: #f1f5f9;
  color: #475569;
}

/* Buttons group inside actions */
.action-buttons-group {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-action {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.35rem;
  border-radius: 0.35rem;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-action:hover {
  background: #f1f5f9;
  color: #475569;
}

.btn-action.btn-save:hover {
  color: #16a34a;
  background: #f0fdf4;
}

.btn-action.btn-cancel:hover {
  color: #dc2626;
  background: #fef2f2;
}

.btn-action.btn-edit:hover {
  color: #2563eb;
  background: #eff6ff;
}

.btn-action.btn-delete:hover {
  color: #ef4444;
  background: #fef2f2;
}

.btn-confirm-delete {
  background: #ef4444;
  color: white;
  border: none;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.35rem 0.6rem;
  border-radius: 0.35rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-confirm-delete:hover {
  background: #dc2626;
}

/* Button & controls global styling */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.65rem 1.25rem;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
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

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Toast and Alert notifications */
.toast-alert {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  z-index: 1000;
  padding: 0.75rem 1.5rem;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.9rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  max-width: 380px;
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

/* Loading Spinners */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 1.25rem;
  gap: 1rem;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(37, 99, 235, 0.15);
  border-radius: 50%;
  border-top-color: #2563eb;
  animation: spin 0.8s linear infinite;
}

.spinner.large {
  width: 36px;
  height: 36px;
  border-width: 4px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.empty-state h3 {
  margin: 0.5rem 0 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
}

.empty-state p {
  margin: 0;
  font-size: 0.9rem;
  color: #64748b;
}

.whitespace-nowrap {
  white-space: nowrap;
}

.text-right {
  text-align: right;
}

.text-center {
  text-align: center;
}

.text-success { color: #16a34a; }
.text-danger { color: #dc2626; }

@keyframes slideIn {
  from { transform: translateX(100%) translateY(-20px); opacity: 0; }
  to { transform: translateX(0) translateY(0); opacity: 1; }
}
</style>
