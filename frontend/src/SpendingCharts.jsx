
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid
} from 'recharts'

import './SpendingCharts.css'

const COLORS = [
  '#8055e8',
  '#ff9f43',
  '#36b37e',
  '#3987f7',
  '#e65c9c',
  '#16a6b6'
]

function SpendingCharts({ transactions }) {
  const expenseTransactions = transactions.filter(
  item => item.type === 'Expense'
)
const categoryTotals = expenseTransactions.reduce((result, item) => {
  const amount = Number(item.amount) || 0

  result[item.category] = (result[item.category] || 0) + amount

  return result
}, {})

  const chartData = Object.entries(categoryTotals).map(
    ([category, amount]) => ({
      category,
      amount
    })
  )

  const totalExpenses = chartData.reduce(
    (sum, item) => sum + item.amount,
    0
  )

  const formatCurrency = (amount) =>
    `₹${Number(amount).toLocaleString('en-IN')}`

  return (
    <section className="charts-section">
      <div className="charts-heading">
        <div>
          <span className="charts-tag">FINANCIAL ANALYTICS</span>
          <h2>Spending Overview</h2>
          <p>Understand where your money goes.</p>
        </div>

        <div className="chart-total">
          <span>Total Expenses</span>
          <strong>{formatCurrency(totalExpenses)}</strong>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Category Distribution</h3>
          <p>Expense percentage by category</p>

          {chartData.length === 0 ? (
            <div className="chart-empty">
              No expense data available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  innerRadius={55}
                  paddingAngle={4}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={entry.category}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>

                <Tooltip
                  formatter={(value) => formatCurrency(value)}
                />

                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-card">
          <h3>Category-wise Spending</h3>
          <p>Compare your expenses</p>

          {chartData.length === 0 ? (
            <div className="chart-empty">
              No expense data available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={chartData}
                margin={{ top: 15, right: 10, left: 5, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                />

                <XAxis
                  dataKey="category"
                  tick={{ fontSize: 11 }}
                  interval={0}
                />

                <YAxis
                  tick={{ fontSize: 11 }}
                />

                <Tooltip
                  formatter={(value) => formatCurrency(value)}
                />

                <Bar
                  dataKey="amount"
                  fill="#8055e8"
                  radius={[8, 8, 0, 0]}
                  maxBarSize={55}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </section>
  )
}

export default SpendingCharts
