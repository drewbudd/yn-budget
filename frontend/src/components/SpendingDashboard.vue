<template>
  <section class="dashboard">
    <!-- Premium Summary Cards Grid -->
    <div class="summary-grid">
      <article class="summary-card card-net">
        <div class="card-indicator"></div>
        <span class="card-label">Net</span>
        <p class="card-value">{{ formattedTotalNet }}</p>
      </article>
      <article class="summary-card card-savings">
        <div class="card-indicator"></div>
        <span class="card-label">Savings</span>
        <p class="card-value">{{ formattedSavingsTotal }}</p>
      </article>
      <article class="summary-card card-spending">
        <div class="card-indicator"></div>
        <span class="card-label">Total Spending</span>
        <p class="card-value">{{ formattedTotalSpending }}</p>
      </article>
      <article class="summary-card card-income">
        <div class="card-indicator"></div>
        <span class="card-label">Total Income</span>
        <p class="card-value">{{ formattedTotalIncome }}</p>
      </article>
    </div>

    <!-- Polished Controls Header Card -->
    <div class="header-card">
      <div class="period-toggle-wrapper">
        <span class="toggle-label">Period</span>
        <div class="period-toggle">
          <button 
            type="button"
            class="toggle-btn"
            :class="{ active: period === 'month' }"
            @click="setPeriod('month')"
          >
            Month
          </button>
          <button 
            type="button"
            class="toggle-btn"
            :class="{ active: period === 'year' }"
            @click="setPeriod('year')"
          >
            Year
          </button>
        </div>
      </div>

      <div class="date-nav-wrapper">
        <button 
          type="button"
          @click="navigatePeriod(-1)" 
          class="nav-arrow-btn" 
          :title="period === 'month' ? 'Previous Month' : 'Previous Year'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>

        <div class="selectors">
          <label class="select-label">
            Year
            <select v-model.number="selectedYear" @change="handleSelectionChange" class="form-select">
              <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
            </select>
          </label>
          
          <label v-if="period === 'month'" class="select-label">
            Month
            <select v-model.number="selectedMonth" @change="handleSelectionChange" class="form-select">
              <option v-for="m in 12" :key="m" :value="m">{{ getMonthName(m) }}</option>
            </select>
          </label>

          <label v-if="period === 'month'" class="select-label">
            Lookback
            <input 
              type="number" 
              min="1" 
              max="24" 
              v-model.number="lookbackMonths" 
              @change="handleSelectionChange" 
              class="form-select lookback-input"
            />
          </label>
        </div>

        <button 
          type="button"
          @click="navigatePeriod(1)" 
          class="nav-arrow-btn" 
          :title="period === 'month' ? 'Next Month' : 'Next Year'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
        </button>

        <button 
          type="button"
          @click="jumpToCurrentPeriod" 
          class="btn btn-secondary btn-today" 
          :disabled="isCurrentPeriodActive"
          title="Jump to Current Period"
        >
          Today
        </button>
      </div>
    </div>

    <div class="chart-grid">
      <div class="chart-card full-width-card">
        <h3>Category Trend</h3>
        <div class="chart-filters">
          <label>
            Category
            <select v-model="selectedCategoryForTrend" @change="buildCategoryTrendChart">
              <option :value="null">Select a category</option>
              <option v-for="cat in allCategoriesForTrend" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </label>
        </div>
        <div v-if="selectedCategoryForTrend" class="chart-summary">
          Average Net: {{ formattedCategoryTrendAverage }}
        </div>
        <div v-if="selectedCategoryForTrend" ref="categoryTrendChart" class="chart"></div>
        <p v-else class="chart-empty">Select a category to view trend.</p>
      </div>
      <div class="chart-card full-width-card">
        <h3>Category Totals</h3>
        <div class="two-column-charts">
          <div class="chart-card-small full-width-card-small">
            <h4>Spending by category</h4>
            <div ref="spendingCategoryChart" class="chart"></div>
          </div>
          <div class="chart-card-small full-width-card-small">
            <h4>Income by category</h4>
            <div ref="incomeCategoryChart" class="chart"></div>
          </div>
        </div>
      </div>
      <div class="chart-card full-width-card">
        <h3>Monthly Spending / Income</h3>
        <div ref="monthlyChart" class="chart"></div>
      </div>
      <div class="chart-card" v-if="period === 'month'">
        <h3>Previous Month vs Current Month</h3>
        <div v-if="hasMonthOverMonthData" ref="monthComparisonChart" class="chart"></div>
        <p v-else class="chart-empty">Not enough months to compare.</p>
      </div>
      <div class="chart-card" v-if="period === 'month'">
        <h3>Same Month Last Year</h3>
        <div v-if="hasYearOverYearData" ref="yearComparisonChart" class="chart"></div>
        <p v-else class="chart-empty">Not enough historical data for same month last year.</p>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'

type MonthlyRow = {
  year: number
  month: number
  total: number
  spending: number
  income: number
}

type CategoryRow = {
  category: string
  total: number
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
  }).format(value)

const monthLabel = (row: MonthlyRow) => `${row.year}-${String(row.month).padStart(2, '0')}`

export default {
  setup() {
    const monthlyChart = ref<HTMLDivElement | null>(null)
    const categoryChart = ref<HTMLDivElement | null>(null)
    const incomeCategoryChart = ref<HTMLDivElement | null>(null)
    const spendingCategoryChart = ref<HTMLDivElement | null>(null)
    const categoryTrendChart = ref<HTMLDivElement | null>(null)
    const monthComparisonChart = ref<HTMLDivElement | null>(null)
    const yearComparisonChart = ref<HTMLDivElement | null>(null)
    const monthlyTotals = ref<MonthlyRow[]>([])
    const categoryTotals = ref<CategoryRow[]>([])
    const incomeCategoryTotals = ref<CategoryRow[]>([])
    const spendingCategoryTotals = ref<CategoryRow[]>([])
    const savingsTotal = ref(0)
    const selectedYear = ref<number | null>(null)
    const selectedMonth = ref<number | null>(null)
    const selectedCategoryForTrend = ref<string | null>(null)
    const categoryTrendAverage = ref<number | null>(null)
    const period = ref<'month' | 'year'>('month')
    const lookbackMonths = ref(12)

    const formattedSavingsTotal = computed(() => formatCurrency(savingsTotal.value))
    const formattedCategoryTrendAverage = computed(() =>
      categoryTrendAverage.value !== null ? formatCurrency(categoryTrendAverage.value) : 'N/A',
    )

    const sortedMonthly = computed(() =>
      [...monthlyTotals.value].sort((a, b) =>
        a.year !== b.year ? a.year - b.year : a.month - b.month,
      ),
    )

    const latestMonth = computed(() => sortedMonthly.value.at(-1) || null)
    const selectedMonthRow = computed(() => {
      if (!selectedYear.value || !selectedMonth.value) return null
      return sortedMonthly.value.find(
        (item) => item.year === selectedYear.value && item.month === selectedMonth.value,
      )
    })
    const selectedPreviousMonthRow = computed(() => {
      const selected = selectedMonthRow.value
      if (!selected) return null
      const index = sortedMonthly.value.findIndex(
        (item) => item.year === selected.year && item.month === selected.month,
      )
      return index > 0 ? sortedMonthly.value[index - 1] : null
    })
    const selectedSameMonthLastYearRow = computed(() => {
      const selected = selectedMonthRow.value
      if (!selected) return null
      return sortedMonthly.value.find(
        (item) => item.month === selected.month && item.year === selected.year - 1,
      )
    })

    const hasMonthOverMonthData = computed(
      () => period.value === 'month' && !!selectedMonthRow.value && !!selectedPreviousMonthRow.value,
    )
    const hasYearOverYearData = computed(
      () => period.value === 'month' && !!selectedMonthRow.value && !!selectedSameMonthLastYearRow.value,
    )

    const selectedPeriodTotals = computed(() => {
      if (!selectedYear.value) {
        return { spending: 0, income: 0, total: 0 }
      }

      if (period.value === 'month' && selectedMonth.value) {
        const item = sortedMonthly.value.find(
          (row) => row.year === selectedYear.value && row.month === selectedMonth.value,
        )
        const spending = Number(item?.spending || 0)
        const previousIncome = Number(selectedPreviousMonthRow.value?.income || 0)
        return {
          spending,
          income: previousIncome,
          total: spending + previousIncome,
        }
      }

      const yearItems = sortedMonthly.value.filter((row) => row.year === selectedYear.value)
      return yearItems.reduce(
        (acc, row) => ({
          spending: acc.spending + Number(row.spending),
          income: acc.income + Number(row.income),
          total: acc.total + Number(row.total),
        }),
        { spending: 0, income: 0, total: 0 },
      )
    })

    const adjustedIncomePeriod = computed(() => {
      if (period.value === 'month') {
        if (!selectedMonth.value || !selectedYear.value) return null
        let adjMonth = selectedMonth.value - 1
        let adjYear = selectedYear.value
        if (adjMonth === 0) {
          adjMonth = 12
          adjYear -= 1
        }
        return { period: 'month', year: adjYear, month: adjMonth }
      } else if (period.value === 'year') {
        if (!selectedYear.value) return null
        return { period: 'year', year: selectedYear.value - 1 }
      }
      return null
    })

    const totalIncomeAdjusted = computed(() =>
      incomeCategoryTotals.value.reduce((sum, item) => sum + Number(item.total), 0),
    )

    const formattedTotalNet = computed(() => formatCurrency(selectedPeriodTotals.value.total))
    const formattedTotalSpending = computed(() => formatCurrency(selectedPeriodTotals.value.spending))
    const formattedTotalIncome = computed(() => formatCurrency(totalIncomeAdjusted.value))

    const availableYears = computed(() => {
      const years = new Set(sortedMonthly.value.map((item) => item.year))
      if (selectedYear.value) {
        years.add(selectedYear.value)
      }
      return Array.from(years).sort((a, b) => b - a)
    })

    const currentRealYear = new Date().getFullYear()
    const currentRealMonth = new Date().getMonth() + 1

    const getMonthName = (m: number) => {
      const date = new Date(2000, m - 1, 1)
      return date.toLocaleString('default', { month: 'long' })
    }

    const setPeriod = async (p: 'month' | 'year') => {
      period.value = p
      await handleSelectionChange()
    }

    const navigatePeriod = async (direction: number) => {
      if (period.value === 'month') {
        let m = (selectedMonth.value || currentRealMonth) + direction
        let y = selectedYear.value || currentRealYear
        if (m === 0) {
          m = 12
          y -= 1
        } else if (m === 13) {
          m = 1
          y += 1
        }
        selectedMonth.value = m
        selectedYear.value = y
      } else {
        selectedYear.value = (selectedYear.value || currentRealYear) + direction
      }
      await handleSelectionChange()
    }

    const jumpToCurrentPeriod = async () => {
      selectedYear.value = currentRealYear
      selectedMonth.value = currentRealMonth
      await handleSelectionChange()
    }

    const isCurrentPeriodActive = computed(() => {
      if (period.value === 'month') {
        return selectedYear.value === currentRealYear && selectedMonth.value === currentRealMonth
      } else {
        return selectedYear.value === currentRealYear
      }
    })
    const availableMonths = computed(() =>
      Array.from(new Set(sortedMonthly.value.map((item) => item.month))).sort((a, b) => a - b),
    )
    const availableMonthsForYear = computed(() => {
      if (!selectedYear.value) {
        return availableMonths.value
      }
      return Array.from(
        new Set(
          sortedMonthly.value
            .filter((item) => item.year === selectedYear.value)
            .map((item) => item.month),
        ),
      ).sort((a, b) => a - b)
    })

    const allCategoriesForTrend = computed(() => {
      return categoryTotals.value.map(item => item.category).sort()
    })

    const monthlyWithPriorIncome = computed(() =>
      sortedMonthly.value.map((item, index, all) => ({
        ...item,
        priorIncome: index > 0 ? all[index - 1].income : 0,
      })),
    )

    const buildMonthlyChart = () => {
      if (!monthlyChart.value || sortedMonthly.value.length === 0) return
      const chart = echarts.init(monthlyChart.value)

      let periodData
      if (period.value === 'year' && selectedYear.value) {
        // Show full selected year
        periodData = monthlyWithPriorIncome.value.filter(item => item.year === selectedYear.value)
      } else {
        // Existing logic for month period
        let endIndex = sortedMonthly.value.length - 1

        if (period.value === 'month' && selectedYear.value && selectedMonth.value) {
          const foundIndex = sortedMonthly.value.findIndex(
            (item) => item.year === selectedYear.value && item.month === selectedMonth.value,
          )
          if (foundIndex >= 0) {
            endIndex = foundIndex
          }
        } else if (selectedYear.value) {
          const yearIndexes = sortedMonthly.value
            .map((item, index) => (item.year === selectedYear.value ? index : -1))
            .filter((index) => index >= 0)
          if (yearIndexes.length > 0) {
            endIndex = yearIndexes[yearIndexes.length - 1]
          }
        }

        const startIndex = Math.max(0, endIndex - lookbackMonths.value + 1)
        periodData = monthlyWithPriorIncome.value.slice(startIndex, endIndex + 1)
      }

      const labels = periodData.map((item) => monthLabel(item))

      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params: any) =>
            params
              .map(
                (entry: any) => `${entry.marker} ${entry.seriesName}: ${formatCurrency(entry.value)}`,
              )
              .join('<br/>'),
        },
        legend: { data: ['Prior Month Income', 'Spending', 'Budget Net'] },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { rotate: 30 },
        },
        yAxis: {
          type: 'value',
          axisLabel: { formatter: '{value} €' },
        },
        series: [
          {
            name: 'Prior Month Income',
            type: 'bar',
            stack: 'budget',
            itemStyle: { color: '#10b981' },
            data: periodData.map((item) => Number(item.priorIncome)),
          },
          {
            name: 'Spending',
            type: 'bar',
            stack: 'budget',
            itemStyle: { color: '#ef4444' },
            data: periodData.map((item) => Number(item.spending)),
          },
          {
            name: 'Budget Net',
            type: 'line',
            itemStyle: { color: '#2563eb' },
            data: periodData.map(
              (item) => Number(item.priorIncome) + Number(item.spending),
            ),
          },
        ],
      })
    }

    const buildCategoryChart = () => {
      if (!categoryChart.value || categoryTotals.value.length === 0) return
      const chart = echarts.init(categoryChart.value)
      chart.setOption({
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} € ({d}%)',
        },
        series: [
          {
            name: 'Categories',
            type: 'pie',
            radius: ['35%', '65%'],
            avoidLabelOverlap: false,
            label: { show: true, formatter: '{b}: {c} €' },
            data: categoryTotals.value.map((item) => ({
              name: item.category,
              value: Number(item.total),
            })),
          },
        ],
      })
    }

    const buildSpendingCategoryChart = () => {
      if (!spendingCategoryChart.value || spendingCategoryTotals.value.length === 0) return
      const chart = echarts.init(spendingCategoryChart.value)
      chart.setOption({
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} € ({d}%)',
        },
        series: [
          {
            name: 'Spending',
            type: 'pie',
            radius: ['35%', '65%'],
            avoidLabelOverlap: false,
            label: { show: true, formatter: '{b}: {c} €' },
            data: spendingCategoryTotals.value.map((item) => ({
              name: item.category,
              value: Number(item.total),
            })),
          },
        ],
      })
    }

    const buildIncomeCategoryChart = () => {
      if (!incomeCategoryChart.value || incomeCategoryTotals.value.length === 0) return
      const chart = echarts.init(incomeCategoryChart.value)
      chart.setOption({
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} € ({d}%)',
        },
        series: [
          {
            name: 'Income',
            type: 'pie',
            radius: ['35%', '65%'],
            avoidLabelOverlap: false,
            label: { show: true, formatter: '{b}: {c} €' },
            data: incomeCategoryTotals.value.map((item) => ({
              name: item.category,
              value: Number(item.total),
            })),
          },
        ],
      })
    }

    const buildCategoryTrendChart = async () => {
      if (!categoryTrendChart.value || !selectedCategoryForTrend.value || !selectedYear.value) return
      const params = new URLSearchParams()
      params.set('category', selectedCategoryForTrend.value)
      params.set('period', period.value)
      params.set('year', String(selectedYear.value))
      if (period.value === 'month' && selectedMonth.value) {
        params.set('month', String(selectedMonth.value))
        params.set('lookback_months', String(lookbackMonths.value))
      }
      const response = await fetch(`/stats/category-trend/?${params.toString()}`)
      const data = await response.json()
      const chart = echarts.init(categoryTrendChart.value)
      const items = data.monthly_totals as MonthlyRow[]
      const valueMap = new Map(
        items.map((item) => [`${item.year}-${String(item.month).padStart(2, '0')}`, item]),
      )

      const rangeMonths: Array<{ year: number; month: number }> = []
      if (period.value === 'year' && selectedYear.value) {
        for (let m = 1; m <= 12; m += 1) {
          rangeMonths.push({ year: selectedYear.value, month: m })
        }
      } else if (period.value === 'month' && selectedYear.value && selectedMonth.value) {
        let year = selectedYear.value
        let month = selectedMonth.value
        for (let i = 0; i < lookbackMonths.value; i += 1) {
          rangeMonths.unshift({ year, month })
          month -= 1
          if (month === 0) {
            month = 12
            year -= 1
          }
        }
      } else {
        rangeMonths.push(...items.map((item) => ({ year: item.year, month: item.month })))
      }

      const labels = rangeMonths.map((item) => monthLabel(item))
      const incomeValues = rangeMonths.map((item) => {
        const key = `${item.year}-${String(item.month).padStart(2, '0')}`
        return Number(valueMap.get(key)?.income || 0)
      })
      const spendingValues = rangeMonths.map((item) => {
        const key = `${item.year}-${String(item.month).padStart(2, '0')}`
        return Number(valueMap.get(key)?.spending || 0)
      })
      const netValues = rangeMonths.map((item) => {
        const key = `${item.year}-${String(item.month).padStart(2, '0')}`
        return Number(valueMap.get(key)?.total || 0)
      })
      const averageNet = netValues.length
        ? netValues.reduce((sum, value) => sum + value, 0) / netValues.length
        : 0
      categoryTrendAverage.value = averageNet
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params: any) =>
            params
              .map(
                (entry: any) => `${entry.marker} ${entry.seriesName}: ${formatCurrency(entry.value)}`,
              )
              .join('<br/>'),
        },
        legend: { data: ['Income', 'Spending', 'Net', 'Average Net'] },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { rotate: 30 },
        },
        yAxis: {
          type: 'value',
          axisLabel: { formatter: '{value} €' },
        },
        series: [
          {
            name: 'Income',
            type: 'bar',
            itemStyle: { color: '#10b981' },
            data: incomeValues,
          },
          {
            name: 'Spending',
            type: 'bar',
            itemStyle: { color: '#ef4444' },
            data: spendingValues,
          },
          {
            name: 'Net',
            type: 'line',
            itemStyle: { color: '#2563eb' },
            data: netValues,
          },
          {
            name: 'Average Net',
            type: 'line',
            itemStyle: { color: '#f59e0b' },
            lineStyle: { type: 'dashed' },
            data: Array(labels.length).fill(averageNet),
          },
        ],
      })
    }

    const buildMonthComparisonChart = () => {
      if (!monthComparisonChart.value || !hasMonthOverMonthData.value) return
      const chart = echarts.init(monthComparisonChart.value)
      const labels = [
        monthLabel(selectedPreviousMonthRow.value as MonthlyRow),
        monthLabel(selectedMonthRow.value as MonthlyRow),
      ]
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params: any) =>
            params
              .map(
                (entry: any) => `${entry.marker} ${entry.seriesName}: ${formatCurrency(entry.value)}`,
              )
              .join('<br/>'),
        },
        legend: { data: ['Income', 'Spending', 'Net'] },
        xAxis: { type: 'category', data: labels },
        yAxis: { type: 'value', axisLabel: { formatter: '{value} €' } },
        series: [
          {
            name: 'Income',
            type: 'bar',
            itemStyle: { color: '#10b981' },
            data: [
              Number(selectedPreviousMonthRow.value?.income || 0),
              Number(selectedMonthRow.value?.income || 0),
            ],
          },
          {
            name: 'Spending',
            type: 'bar',
            itemStyle: { color: '#ef4444' },
            data: [
              Number(selectedPreviousMonthRow.value?.spending || 0),
              Number(selectedMonthRow.value?.spending || 0),
            ],
          },
          {
            name: 'Net',
            type: 'line',
            itemStyle: { color: '#2563eb' },
            data: [
              Number(selectedPreviousMonthRow.value?.total || 0),
              Number(selectedMonthRow.value?.total || 0),
            ],
          },
        ],
      })
    }

    const buildYearComparisonChart = () => {
      if (!yearComparisonChart.value || !hasYearOverYearData.value) return
      const chart = echarts.init(yearComparisonChart.value)
      const labels = [
        monthLabel(selectedSameMonthLastYearRow.value as MonthlyRow),
        monthLabel(selectedMonthRow.value as MonthlyRow),
      ]
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params: any) =>
            params
              .map(
                (entry: any) => `${entry.marker} ${entry.seriesName}: ${formatCurrency(entry.value)}`,
              )
              .join('<br/>'),
        },
        legend: { data: ['Income', 'Spending', 'Net'] },
        xAxis: { type: 'category', data: labels },
        yAxis: { type: 'value', axisLabel: { formatter: '{value} €' } },
        series: [
          {
            name: 'Income',
            type: 'bar',
            itemStyle: { color: '#10b981' },
            data: [
              Number(selectedSameMonthLastYearRow.value?.income || 0),
              Number(selectedMonthRow.value?.income || 0),
            ],
          },
          {
            name: 'Spending',
            type: 'bar',
            itemStyle: { color: '#ef4444' },
            data: [
              Number(selectedSameMonthLastYearRow.value?.spending || 0),
              Number(selectedMonthRow.value?.spending || 0),
            ],
          },
          {
            name: 'Net',
            type: 'line',
            itemStyle: { color: '#2563eb' },
            data: [
              Number(selectedSameMonthLastYearRow.value?.total || 0),
              Number(selectedMonthRow.value?.total || 0),
            ],
          },
        ],
      })
    }

    const fetchCategoryTotals = async () => {
      if (!selectedYear.value) return

      // Fetch spending for selected period
      const spendingParams = new URLSearchParams()
      spendingParams.set('period', period.value)
      spendingParams.set('year', String(selectedYear.value))
      if (period.value === 'month' && selectedMonth.value) {
        spendingParams.set('month', String(selectedMonth.value))
      }
      const spendingResponse = await fetch(`/stats/categories/?${spendingParams.toString()}`)
      const spendingData = await spendingResponse.json()
      spendingCategoryTotals.value = spendingData.spending_category_totals
      savingsTotal.value = Number(spendingData.savings_total || 0)

      // Fetch income for adjusted period
      const incomeParams = new URLSearchParams()
      const adj = adjustedIncomePeriod.value
      if (adj) {
        if (adj.period === 'month') {
          incomeParams.set('period', 'month')
          incomeParams.set('year', String(adj.year))
          incomeParams.set('month', String(adj.month))
        } else if (adj.period === 'year') {
          // Custom range: Dec of adj.year to Nov of selectedYear
          incomeParams.set('start_year', String(adj.year))
          incomeParams.set('start_month', '12')
          incomeParams.set('end_year', String(selectedYear.value))
          incomeParams.set('end_month', '11')
        }
      } else {
        // Fallback to selected period
        incomeParams.set('period', period.value)
        incomeParams.set('year', String(selectedYear.value))
        if (period.value === 'month' && selectedMonth.value) {
          incomeParams.set('month', String(selectedMonth.value))
        }
      }
      const incomeResponse = await fetch(`/stats/categories/?${incomeParams.toString()}`)
      const incomeData = await incomeResponse.json()
      incomeCategoryTotals.value = incomeData.income_category_totals

      await nextTick()
      buildSpendingCategoryChart()
      buildIncomeCategoryChart()
    }

    const handleSelectionChange = async () => {
      await fetchCategoryTotals()
      await nextTick()
      buildMonthlyChart()
      if (period.value === 'month') {
        buildMonthComparisonChart()
        buildYearComparisonChart()
      }
      if (selectedCategoryForTrend.value) {
        await buildCategoryTrendChart()
      }
    }

    const loadStats = async () => {
      const response = await fetch('/stats/')
      const data = await response.json()
      monthlyTotals.value = data.monthly_totals
      categoryTotals.value = data.category_totals
      const latest = monthlyTotals.value.at(-1)
      selectedYear.value = latest?.year ?? new Date().getFullYear()
      selectedMonth.value = latest?.month ?? new Date().getMonth() + 1
      if (availableYears.value.length > 0 && !availableYears.value.includes(selectedYear.value)) {
        selectedYear.value = availableYears.value[0]
      }
      if (period.value === 'month') {
        if (availableMonthsForYear.value.length > 0 && !availableMonthsForYear.value.includes(selectedMonth.value || 0)) {
          selectedMonth.value = availableMonthsForYear.value[0]
        }
      } else if (availableMonths.value.length > 0 && !availableMonths.value.includes(selectedMonth.value || 0)) {
        selectedMonth.value = availableMonths.value[0]
      }
      buildMonthlyChart()
      buildCategoryChart()
      await nextTick()
      buildMonthComparisonChart()
      buildYearComparisonChart()
      await fetchCategoryTotals()
    }

    onMounted(loadStats)

    return {
      monthlyChart,
      categoryChart,
      incomeCategoryChart,
      spendingCategoryChart,
      monthComparisonChart,
      yearComparisonChart,
      selectedYear,
      selectedMonth,
      period,
      lookbackMonths,
      availableYears,
      availableMonths,
      availableMonthsForYear,
      allCategoriesForTrend,
      selectedCategoryForTrend,
      categoryTrendChart,
      adjustedIncomePeriod,
      formattedTotalNet,
      formattedTotalSpending,
      formattedTotalIncome,
      formattedSavingsTotal,
      formattedCategoryTrendAverage,
      savingsTotal,
      hasMonthOverMonthData,
      hasYearOverYearData,
      fetchCategoryTotals,
      handleSelectionChange,
      buildCategoryTrendChart,
      getMonthName,
      setPeriod,
      navigatePeriod,
      jumpToCurrentPeriod,
      isCurrentPeriodActive,
    }
  },
}
</script>

<style scoped>
.dashboard {
  display: grid;
  gap: 1.5rem;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
}
.summary-card {
  position: relative;
  padding: 1.5rem;
  border-radius: 1.25rem;
  background: white;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow: hidden;
  transition: all 0.25s ease;
}
.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px -2px rgba(15, 23, 42, 0.08);
}
.card-indicator {
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
}
.card-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}
.card-value {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 800;
  color: #0f172a;
}
/* Card Specific Colors */
.card-net .card-indicator { background-color: #2563eb; }
.card-savings .card-indicator { background-color: #10b981; }
.card-spending .card-indicator { background-color: #ef4444; }
.card-income .card-indicator { background-color: #10b981; }

.header-card {
  background: white;
  padding: 1.5rem;
  border-radius: 1.25rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin: 1.5rem 0;
}

@media(min-width: 768px) {
  .header-card {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.period-toggle-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toggle-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

.period-toggle {
  display: flex;
  background: #f1f5f9;
  padding: 0.25rem;
  border-radius: 0.75rem;
}

.toggle-btn {
  padding: 0.4rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: #475569;
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn.active {
  background: white;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
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

.lookback-input {
  width: 70px;
  min-width: 70px;
  text-align: center;
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

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
.chart-filters label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.95rem;
}
.chart-filters select {
  padding: 0.4rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  background: white;
}
.two-column-charts {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
}
.full-width-card-small {
  grid-column: span 2;
}
.chart-card-small {
  background: #f8fafc;
  padding: 0.75rem;
  border-radius: 0.75rem;
}
.chart-card h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
}
.chart-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(2, minmax(360px, 1fr));
}
.chart-card {
  padding: 1.5rem;
  border-radius: 1.25rem;
  background: white;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
}
.full-width-card {
  grid-column: span 2;
}
.chart-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1rem;
}
.chart-summary {
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.75rem;
}

.chart {
  min-height: 360px;
}
.chart-empty {
  margin: 0;
  padding: 1rem;
  color: #6b7280;
  font-size: 0.95rem;
}
</style>
