<template>
  <section class="transaction-importer">
    <!-- Status Toast Alert -->
    <div v-if="toastMessage" class="toast-alert" :class="toastClass">
      {{ toastMessage }}
    </div>

    <!-- Header Section -->
    <div class="header-card">
      <div class="title-section">
        <h2>Import Transactions</h2>
        <p>Upload a transaction CSV file from your bank to analyze and import them into SQLite.</p>
      </div>
      
      <!-- File Selector Dropzone -->
      <div 
        v-if="!previewRows.length" 
        class="dropzone-area"
        :class="{ dragging: isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleFileDrop"
        @click="triggerFileSelect"
      >
        <input 
          type="file" 
          ref="fileInput" 
          @change="handleFileSelect" 
          accept=".csv" 
          class="file-input-hidden" 
        />
        <div class="dropzone-content">
          <div class="icon-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          </div>
          <h3>Select or drag a CSV file</h3>
          <p>Standard bank CSV export format containing Booking Date, Amount (EUR), etc.</p>
          <button class="btn btn-secondary btn-select">Browse File</button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner large"></div>
      <p>{{ loadingText }}</p>
    </div>

    <!-- Preview Dashboard Section -->
    <div v-if="previewRows.length && !loading" class="preview-container">
      <!-- Summary metrics cards -->
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="label">Total Rows</span>
          <span class="value">{{ totalCount }}</span>
        </div>
        <div class="metric-card card-warning">
          <span class="label">Predicted Categories</span>
          <span class="value">{{ predictedCount }}</span>
        </div>
        <div class="metric-card card-danger">
          <span class="label">Skipped Duplicates</span>
          <span class="value text-danger">{{ duplicateCount }}</span>
        </div>
      </div>

      <!-- Preview Table Controls -->
      <div class="actions-bar">
        <div class="left-actions">
          <button @click="resetPreview" class="btn btn-secondary" :disabled="isImporting">
            Cancel
          </button>
        </div>
        <div class="right-actions">
          <button @click="confirmImport" class="btn btn-primary" :disabled="isImporting">
            <span v-if="isImporting" class="spinner"></span>
            {{ isImporting ? 'Importing...' : 'Confirm Import' }}
          </button>
        </div>
      </div>

      <!-- Preview Table -->
      <div class="table-card">
        <div class="table-responsive">
          <table class="preview-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Partner</th>
                <th>Category Selection</th>
                <th>Prediction Suggestion</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Amount</th>
                <th class="text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="(row, idx) in previewRows" 
                :key="row.row_id || idx"
                :class="{ 'row-duplicate': row.duplicate_in_db }"
              >
                <td class="whitespace-nowrap">{{ formatDate(row.booking_date) }}</td>
                <td class="partner-cell" :title="row.partner_name">{{ row.partner_name || '-' }}</td>
                <td>
                  <select v-model="row.category" class="table-select">
                    <option value="">Uncategorized</option>
                    <option v-for="opt in categoryChoices" :key="opt" :value="opt">
                      {{ opt }}
                    </option>
                  </select>
                </td>
                <td>
                  <span v-if="row.is_low_confidence_suggestion" class="badge badge-low-conf">
                    {{ row.predicted_category }}
                  </span>
                  <span v-else-if="row.was_predicted" class="badge badge-predicted">
                    {{ row.predicted_category }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="row.prediction_confidence" class="conf-text" :class="getConfidenceClass(row.prediction_confidence)">
                    {{ Math.round(row.prediction_confidence * 100) }}%
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="row.duplicate_in_db" class="badge badge-error">
                    Duplicate (Will Skip)
                  </span>
                  <span v-else class="badge badge-success">
                    Ready
                  </span>
                </td>
                <td class="amount-cell" :class="row.amount_eur.startsWith('-') ? 'negative' : 'positive'">
                  {{ formatCurrency(parseFloat(row.amount_eur)) }}
                </td>
                <td class="text-center">
                  <button @click="deleteRow(idx)" class="btn-delete" title="Remove from list">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Recent Transactions Section -->
    <div v-if="!previewRows.length && !loading" class="recent-container">
      <div class="section-title">
        <h3>Recent Transactions</h3>
        <p>The last 10 transactions imported into the SQLite database.</p>
      </div>

      <div class="table-card">
        <div v-if="loadingRecent" class="loading-state-recent">
          <div class="spinner"></div>
          <p>Updating transactions...</p>
        </div>
        <div v-else-if="recentTransactions.length === 0" class="empty-state">
          <p>No transactions imported yet. Use the uploader above to get started.</p>
        </div>
        <div v-else class="table-responsive">
          <table class="recent-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Partner</th>
                <th>Category</th>
                <th>Type</th>
                <th class="text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(t, index) in recentTransactions" :key="index">
                <td class="whitespace-nowrap">{{ formatDate(t.booking_date) }}</td>
                <td class="partner-cell" :title="t.partner_name">{{ t.partner_name || '-' }}</td>
                <td>
                  <span class="badge badge-light">{{ t.category }}</span>
                </td>
                <td class="type-cell">{{ t.transaction_type }}</td>
                <td class="amount-cell text-right" :class="t.amount_eur.startsWith('-') ? 'negative' : 'positive'">
                  {{ formatCurrency(parseFloat(t.amount_eur)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { ref, onMounted, computed } from 'vue'

interface PreviewRow {
  row_id?: number
  booking_date: string
  value_date: string | null
  partner_name: string
  category: string | null
  amount_eur: string
  payment_reference: string
  partner_iban: string
  transaction_type: string
  account_name: string
  original_amount: string | null
  original_currency: string
  exchange_rate: string | null
  prediction_confidence: number | null
  was_predicted: boolean
  predicted_category: string | null
  is_low_confidence_suggestion: boolean
  duplicate_in_db: boolean
}

interface RecentTransaction {
  booking_date: string
  value_date: string | null
  partner_name: string
  category: string
  amount_eur: string
  transaction_type: string
}

export default {
  setup() {
    const fileInput = ref<HTMLInputElement | null>(null)
    const isDragging = ref(false)
    const previewRows = ref<PreviewRow[]>([])
    const categoryChoices = ref<string[]>([])
    
    // Status states
    const loading = ref(false)
    const loadingText = ref('Analyzing CSV data...')
    const isImporting = ref(false)
    const toastMessage = ref('')
    const toastClass = ref('')
    
    // Recent transactions
    const recentTransactions = ref<RecentTransaction[]>([])
    const loadingRecent = ref(false)

    // Derived summary info
    const totalCount = computed(() => previewRows.value.length)
    const duplicateCount = computed(() => previewRows.value.filter(r => r.duplicate_in_db).length)
    const predictedCount = computed(() => previewRows.value.filter(r => r.was_predicted || r.is_low_confidence_suggestion).length)

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

    const getConfidenceClass = (conf: number) => {
      if (conf >= 0.8) return 'conf-high'
      if (conf >= 0.5) return 'conf-medium'
      return 'conf-low'
    }

    const showToast = (message: string, isError = false) => {
      toastMessage.value = message
      toastClass.value = isError ? 'alert-danger' : 'alert-success'
      setTimeout(() => {
        toastMessage.value = ''
      }, 5000)
    }

    const getCsrfToken = (): string => {
      const name = 'csrftoken'
      const cookieValue = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)')
      return cookieValue ? cookieValue.pop() || '' : ''
    }

    // Load recent transactions from API
    const fetchRecentTransactions = async () => {
      loadingRecent.value = true
      try {
        const response = await fetch('/api/transactions/recent/')
        if (!response.ok) throw new Error()
        const data = await response.json()
        recentTransactions.value = data.recent_transactions
      } catch (err) {
        showToast('Failed to load recent transactions', true)
      } finally {
        loadingRecent.value = false
      }
    }

    // Trigger standard file selection input
    const triggerFileSelect = () => {
      fileInput.value?.click()
    }

    // Handles files input selection
    const handleFileSelect = (event: Event) => {
      const target = event.target as HTMLInputElement
      if (target.files && target.files.length > 0) {
        uploadFile(target.files[0])
      }
    }

    // Handles dragging drops
    const handleFileDrop = (event: DragEvent) => {
      isDragging.value = false
      if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
        uploadFile(event.dataTransfer.files[0])
      }
    }

    // Upload file to get preview
    const uploadFile = async (file: File) => {
      if (!file.name.endsWith('.csv')) {
        showToast('Please upload a valid CSV file', true)
        return
      }

      loading.value = true
      loadingText.value = 'Uploading and analyzing CSV transactions...'
      
      const formData = new FormData()
      formData.append('file', file)

      try {
        const response = await fetch('/api/transactions/preview/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken()
          },
          body: formData
        })

        if (!response.ok) {
          const errText = await response.text()
          throw new Error(errText || 'Failed to parse CSV file')
        }

        const data = await response.json()
        previewRows.value = data.preview_rows
        categoryChoices.value = data.category_choices
        showToast(`Successfully analyzed file. Review ${data.total_count} rows before importing.`)
      } catch (err: any) {
        showToast(err.message || 'Error parsing the CSV file. Check formatting.', true)
      } finally {
        loading.value = false
      }
    }

    // Deletes row locally from preview list
    const deleteRow = (index: number) => {
      previewRows.value.splice(index, 1)
      showToast('Row removed from preview list.')
    }

    // Resets preview state
    const resetPreview = () => {
      previewRows.value = []
      categoryChoices.value = []
      if (fileInput.value) fileInput.value.value = ''
    }

    // Submit import to backend
    const confirmImport = async () => {
      isImporting.value = true
      loading.value = true
      loadingText.value = 'Saving transactions to database & training ML model...'

      try {
        const response = await fetch('/api/transactions/confirm/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            transactions: previewRows.value
          })
        })

        if (!response.ok) throw new Error('Failed to import')
        
        const result = await response.json()
        showToast(
          `Import complete! Created: ${result.created_count} transactions. Skipped duplicates: ${result.skipped_count}.`
        )
        resetPreview()
        await fetchRecentTransactions()
      } catch (err) {
        showToast('Failed to complete transaction import', true)
      } finally {
        isImporting.value = false
        loading.value = false
      }
    }

    onMounted(() => {
      fetchRecentTransactions()
    })

    return {
      fileInput,
      isDragging,
      previewRows,
      categoryChoices,
      loading,
      loadingText,
      isImporting,
      toastMessage,
      toastClass,
      recentTransactions,
      loadingRecent,
      totalCount,
      duplicateCount,
      predictedCount,
      formatCurrency,
      formatDate,
      getConfidenceClass,
      triggerFileSelect,
      handleFileSelect,
      handleFileDrop,
      deleteRow,
      resetPreview,
      confirmImport
    }
  }
}
</script>

<style scoped>
.transaction-importer {
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
}

.title-section h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.title-section p {
  margin: 0.35rem 0 1.5rem;
  color: #64748b;
  font-size: 0.95rem;
}

/* Uploader drag and dropzone styling */
.dropzone-area {
  border: 2px dashed #cbd5e1;
  border-radius: 1rem;
  padding: 3rem 1.5rem;
  text-align: center;
  cursor: pointer;
  background: #f8fafc;
  transition: all 0.2s ease-in-out;
  display: flex;
  justify-content: center;
}

.dropzone-area:hover, .dropzone-area.dragging {
  border-color: #2563eb;
  background-color: #eff6ff;
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 420px;
}

.icon-circle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  transition: all 0.2s ease;
}

.dropzone-area:hover .icon-circle, .dropzone-area.dragging .icon-circle {
  background: #2563eb;
  color: white;
  transform: scale(1.05);
}

.dropzone-content h3 {
  margin: 0 0 0.4rem;
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
}

.dropzone-content p {
  margin: 0 0 1.5rem;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.5;
}

.file-input-hidden {
  display: none;
}

/* Button & controls styling */
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

.btn-select {
  padding: 0.5rem 1.25rem;
  font-size: 0.85rem;
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

/* Metrics and Cards */
.preview-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  animation: slideUp 0.3s ease-out;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
}

.metric-card {
  background: white;
  padding: 1.25rem 1.5rem;
  border-radius: 1rem;
  border: 1.5px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.metric-card.card-warning {
  border-left: 4px solid #f59e0b;
}

.metric-card.card-danger {
  border-left: 4px solid #ef4444;
}

.metric-card .label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  font-weight: 600;
}

.metric-card .value {
  font-size: 1.75rem;
  font-weight: 800;
  color: #0f172a;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Table styling */
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
}

.preview-table, .recent-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.9rem;
}

.preview-table th, .recent-table th {
  background: #f8fafc;
  padding: 0.85rem 1rem;
  font-weight: 700;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.preview-table td, .recent-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: middle;
}

.preview-table tr:last-child td, .recent-table tr:last-child td {
  border-bottom: none;
}

.preview-table tr.row-duplicate {
  background: #fff8f8;
}

.preview-table tr.row-duplicate td {
  border-bottom-color: #fee2e2;
}

.partner-cell {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.type-cell {
  color: #64748b;
}

.amount-cell {
  font-weight: 700;
  text-align: right;
  white-space: nowrap;
}

.amount-cell.negative {
  color: #dc2626;
}

.amount-cell.positive {
  color: #16a34a;
}

/* Badges and Select fields */
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
  max-width: 160px;
}

.table-select:focus {
  border-color: #2563eb;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
}

.badge-predicted {
  background-color: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.badge-low-conf {
  background-color: #fffbeb;
  color: #d97706;
  border: 1px solid #fde68a;
  font-style: italic;
}

.badge-success {
  background-color: #f0fdf4;
  color: #16a34a;
}

.badge-error {
  background-color: #fef2f2;
  color: #dc2626;
}

.badge-light {
  background-color: #f1f5f9;
  color: #475569;
}

.conf-text {
  font-weight: 700;
  font-size: 0.85rem;
}

.conf-high { color: #16a34a; }
.conf-medium { color: #d97706; }
.conf-low { color: #dc2626; }

.btn-delete {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.35rem;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-delete:hover {
  color: #ef4444;
  background: #fef2f2;
}

/* Loading & Toast Alerts */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 1.25rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  gap: 1rem;
}

.loading-state-recent {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2.5rem;
  color: #64748b;
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

/* Recent Container */
.recent-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  animation: slideUp 0.3s ease-out 0.1s both;
}

.section-title h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.section-title p {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #94a3b8;
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

@keyframes slideIn {
  from { transform: translateX(100%) translateY(-20px); opacity: 0; }
  to { transform: translateX(0) translateY(0); opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(12px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
