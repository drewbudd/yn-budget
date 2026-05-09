<template>
  <section class="dashboard">
    <div class="summary-grid">
      <article class="summary-card">
        <h2>Net</h2>
        <p>{{ formattedTotalNet }}</p>
      </article>
      <article class="summary-card">
        <h2>Savings</h2>
        <p>{{ formattedSavingsTotal }}</p>
      </article>
      <article class="summary-card">
        <h2>Total Spending</h2>
        <p>{{ formattedTotalSpending }}</p>
      </article>
      <article class="summary-card">
        <h2>Total Income</h2>
        <p>{{ formattedTotalIncome }}</p>
      </article>
    </div>

    <div class="dashboard-controls">
      <div class="control-group">
        <span>Period</span>
        <label>
          <input type="radio" name="period" value="month" v-model="period" @change="handleSelectionChange" />
          Month
        </label>
        <label>
          <input type="radio" name="period" value="year" v-model="period" @change="handleSelectionChange" />
          Year
        </label>
      </div>
      <div class="control-group">
        <label>
          Year
          <select v-model.number="selectedYear" @change="handleSelectionChange">
            <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
          </select>
        </label>
        <label v-if="period === 'month'">
          Month
          <select v-model.number="selectedMonth" @change="handleSelectionChange">
            <option v-for="month in availableMonthsForYear" :key="month" :value="month">{{ month }}</option>
          </select>
        </label>
        <label v-if="period === 'month'">
          Previous months
          <input type="number" min="1" max="24" v-model.number="lookbackMonths" @change="handleSelectionChange" />
        </label>
      </div>
    </div>

    <div class="chart-grid">
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
    const monthComparisonChart = ref<HTMLDivElement | null>(null)
    const yearComparisonChart = ref<HTMLDivElement | null>(null)
    const monthlyTotals = ref<MonthlyRow[]>([])
    const categoryTotals = ref<CategoryRow[]>([])
    const incomeCategoryTotals = ref<CategoryRow[]>([])
    const spendingCategoryTotals = ref<CategoryRow[]>([])
    const savingsTotal = ref(0)
    const selectedYear = ref<number | null>(null)
    const selectedMonth = ref<number | null>(null)
    const period = ref<'month' | 'year'>('month')
    const lookbackMonths = ref(12)

    const formattedSavingsTotal = computed(() => formatCurrency(savingsTotal.value))

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
        return {
          spending: Number(item?.spending || 0),
          income: Number(item?.income || 0),
          total: Number(item?.total || 0),
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

    const availableYears = computed(() =>
      Array.from(new Set(sortedMonthly.value.map((item) => item.year))).sort((a, b) => b - a),
    )
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
      adjustedIncomePeriod,
      formattedTotalNet,
      formattedTotalSpending,
      formattedTotalIncome,
      formattedSavingsTotal,
      savingsTotal,
      hasMonthOverMonthData,
      hasYearOverYearData,
      fetchCategoryTotals,
      handleSelectionChange,
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
  gap: 1rem;
}
.summary-card {
  padding: 1rem;
  border-radius: 1rem;
  background: white;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}
.summary-card h2 {
  margin: 0 0 0.6rem;
  font-size: 1rem;
  color: #374151;
}
.summary-card p {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
}
.chart-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(2, minmax(360px, 1fr));
}
.chart-card {
  padding: 1rem;
  border-radius: 1rem;
  background: white;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
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

.dashboard-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin: 1.5rem 0;
  align-items: center;
}

.control-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.control-group label {
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
}

.control-group input[type='number'],
.control-group select {
  margin-top: 0.25rem;
  padding: 0.45rem 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
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
