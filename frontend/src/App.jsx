
import { useState, useEffect } from 'react'

import {
  getTransactions,
  addTransaction as createTransaction,
  updateTransaction as saveTransactionUpdate,
  deleteTransaction as removeTransaction,
  getBudgets,
  addBudget as createBudget,
  updateBudget as saveBudgetUpdate,
  deleteBudget as removeBudget,
  getCategoryRules,
  addCategoryRule,
  updateCategoryRule,
  deleteCategoryRule,
  generateInsights,
getInsights,
updateInsight
} from './services/api'

import { motion } from 'framer-motion'
import SpendingCharts from './SpendingCharts'
import RecurringPayments from './RecurringPayments'

import {
  Wallet,
  TrendingUp,
  TrendingDown,
  PiggyBank,
  ArrowUpRight,
  Bell,
  Search,
  LayoutDashboard,
  Receipt,
  Repeat,
  Target,
  Settings,
  Utensils,
  Car,
  ShoppingBag,
  Tags,
  Plus,
  Pencil,
  Trash2,
  Zap,
  ShieldAlert,
CheckCircle2,
RefreshCw,
AlertTriangle,
Info
} from 'lucide-react'

import './App.css'

function getTransactionIcon(item) {
  if (item.category === 'Income') return Wallet
  if (item.category === 'Food & Dining') return Utensils
  if (item.category === 'Transportation') return Car
  if (item.category === 'Shopping') return ShoppingBag
  return Receipt
}
function formatTransaction(item) {
  const category = item.category_name || item.category || 'Other'
  const type = item.transaction_type || 'Expense'
  const amount = Number(item.amount)

  return {
    id: item.transaction_id,
    name: item.description || item.merchant_name || 'Transaction',
    category,
    date: item.transaction_date || item.date,
    amount: amount,
    icon: getTransactionIcon({ category }),
    color: type === 'Income' || type === 'Refund' ? 'green' : 'orange',
    type
  }
}

function App() {
  // ================================
  // TRANSACTION STATES
  // ================================

  const [loadingTransactions, setLoadingTransactions] = useState(true)
  const [savingTransaction, setSavingTransaction] = useState(false)
  const [transactions, setTransactions] = useState([])

  const [showForm, setShowForm] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [selectedType, setSelectedType] = useState('All')
  const [editId, setEditId] = useState(null)

  // ================================
  // INSIGHT STATES
  // ================================

  const [insights, setInsights] = useState([])
  const [loadingInsights, setLoadingInsights] = useState(true)
  const [generatingInsights, setGeneratingInsights] = useState(false)
  const [updatingInsightId, setUpdatingInsightId] = useState(null)


  const [formData, setFormData] = useState({
    name: '',
    amount: '',
    type: 'Expense',
    category: '',
    date: new Date().toISOString().slice(0, 10)
  })

  // ================================
  // BUDGET STATES
  // ================================

  const [budgets, setBudgets] = useState([])
  const [loadingBudgets, setLoadingBudgets] = useState(true)
  const [savingBudget, setSavingBudget] = useState(false)
  const [editingBudgetId, setEditingBudgetId] = useState(null)

  const [showBudgetForm, setShowBudgetForm] = useState(false)
  const [budgetCategory, setBudgetCategory] = useState('Food & Dining')
  const [budgetAmount, setBudgetAmount] = useState('')

  // ================================
  // CATEGORY RULE STATES
  // ================================

  const [categoryRules, setCategoryRules] = useState([])
  const [loadingRules, setLoadingRules] = useState(true)
  const [savingRule, setSavingRule] = useState(false)
  const [editingRuleId, setEditingRuleId] = useState(null)
  const [showRuleForm, setShowRuleForm] = useState(false)

  const [ruleForm, setRuleForm] = useState({
    rule_name: '',
    category: 'Food & Dining',
    match_field: 'description',
    match_type: 'contains',
    match_value: '',
    priority: 1,
    is_active: true,
    effective_from: new Date().getFullYear() + '-01-01'
  })

  // ================================
  // COMMON MESSAGES
  // ================================

  const [apiError, setApiError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // ================================
  // LOAD TRANSACTIONS
  // ================================

  const loadTransactions = async () => {
    try {
      const data = await getTransactions()

      const records = Array.isArray(data)
        ? data
        : data.transactions || []

      setTransactions(records.map(formatTransaction))
    } catch (error) {
      console.error('Backend transaction error:', error)
      setApiError(
        'Unable to connect to backend. Please check whether Flask is running.'
      )
    } finally {
      setLoadingTransactions(false)
    }
  }

  // ================================
  // LOAD BUDGETS
  // ================================

  const loadBudgets = async () => {
    try {
      const data = await getBudgets()

      const records = Array.isArray(data)
        ? data
        : data.budgets || []

      setBudgets(records)
    } catch (error) {
      console.error('Backend budget error:', error)
      setApiError(error.message || 'Unable to load budgets.')
    } finally {
      setLoadingBudgets(false)
    }
  }

  // ================================
  // LOAD CATEGORY RULES
  // ================================

  const loadCategoryRules = async () => {
    try {
      const data = await getCategoryRules()

      const records = Array.isArray(data)
        ? data
        : data.rules || []

      setCategoryRules(records)
    } catch (error) {
      console.error('Category rules error:', error)
      setApiError(error.message || 'Unable to load category rules.')
    } finally {
      setLoadingRules(false)
    }
  }

  // ================================
  // LOAD INSIGHTS
  // ================================

  const loadInsights = async () => {
    try {
      const data = await getInsights()
      setInsights(data.insights || [])
    } catch (error) {
      console.error('Insight loading error:', error)
      setApiError(error.message || 'Unable to load insights.')
    } finally {
      setLoadingInsights(false)
    }
  }

  // Generate fresh insights from backend
  const handleGenerateInsights = async () => {
    setGeneratingInsights(true)
    setApiError('')
    setSuccessMessage('')

    try {
      const result = await generateInsights()
      await loadInsights()

      setSuccessMessage(
        `${result.generated_or_updated_count} insights generated or updated successfully!`
      )
    } catch (error) {
      console.error('Insight generation error:', error)
      setApiError(error.message || 'Unable to generate insights.')
    } finally {
      setGeneratingInsights(false)
    }
  }

  // Update insight status
  const handleInsightStatus = async (id, status) => {
    setUpdatingInsightId(id)
    setApiError('')
    setSuccessMessage('')

    try {
      await updateInsight(id, status)
      await loadInsights()
      setSuccessMessage(`Insight marked as ${status}.`)
    } catch (error) {
      console.error('Insight status error:', error)
      setApiError(error.message || 'Unable to update insight.')
    } finally {
      setUpdatingInsightId(null)
    }
  }


  useEffect(() => {
  loadTransactions()
  loadBudgets()
  loadCategoryRules()
  loadInsights()
}, [])

  // ================================
  // TRANSACTION FUNCTIONS
  // ================================

  const closeTransactionForm = () => {
    setShowForm(false)
    setEditId(null)

    setFormData({
      name: '',
      amount: '',
      type: 'Expense',
      category: '',
      date: new Date().toISOString().slice(0, 10)
    })
  }

  const editTransaction = (id) => {
    const item = transactions.find(
      transaction => transaction.id === id
    )

    if (!item) return

    setFormData({
      name: item.name,
     amount: String(Number(item.amount) || 0),
type: item.type || 'Expense',
      category: item.category === 'Other' ? '' : item.category,
      date: item.date
    })

    setEditId(id)
    setApiError('')
    setSuccessMessage('')
    setShowForm(true)
  }

  const submitTransaction = async (e) => {
    e.preventDefault()

    const numericAmount = Number(formData.amount)

    if (
      !formData.name.trim() ||
      !Number.isFinite(numericAmount) ||
      numericAmount <= 0 ||
      !formData.date
    ) {
      setApiError('Please enter valid transaction details.')
      return
    }

    const transactionPayload = {
      name: formData.name.trim(),
      amount: numericAmount,
      date: formData.date,
      transaction_type: formData.type,
      ...(formData.category
        ? { category: formData.category }
        : {})
    }

    setSavingTransaction(true)
    setApiError('')
    setSuccessMessage('')

    try {
      let result

      if (editId) {
        result = await saveTransactionUpdate(editId, transactionPayload)
        setSuccessMessage('Transaction updated successfully!')
      } else {
        result = await createTransaction(transactionPayload)

        if (result.categorization_method === 'automatic') {
          setSuccessMessage(
            `Transaction added! Automatically categorized as ${result.category || 'matched category'}.`
          )
        } else if (result.categorization_method === 'uncategorized') {
          setSuccessMessage(
            'Transaction added. No matching rule found, so it is uncategorized.'
          )
        } else {
          setSuccessMessage('Transaction added successfully!')
        }
      }

      closeTransactionForm()
      await loadTransactions()
    } catch (error) {
      console.error('Transaction save error:', error)
      setApiError(error.message || 'Unable to save transaction.')
    } finally {
      setSavingTransaction(false)
    }
  }

  const deleteTransaction = async (id) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this transaction?'
    )

    if (!confirmed) return

    setApiError('')
    setSuccessMessage('')

    try {
      await removeTransaction(id)
      setSuccessMessage('Transaction deleted successfully!')

      if (editId === id) {
        closeTransactionForm()
      }

      await loadTransactions()
    } catch (error) {
      console.error('Transaction delete error:', error)
      setApiError(error.message || 'Unable to delete transaction.')
    }
  }

  // ================================
  // BUDGET FUNCTIONS
  // ================================

  const openBudgetForm = () => {
    setEditingBudgetId(null)
    setBudgetCategory('Food & Dining')
    setBudgetAmount('')
    setApiError('')
    setSuccessMessage('')
    setShowBudgetForm(true)
  }

  const submitBudget = async (e) => {
    e.preventDefault()

    const amount = Number(budgetAmount)

    if (!Number.isFinite(amount) || amount <= 0) {
      setApiError('Please enter a valid positive budget amount.')
      return
    }

    setSavingBudget(true)
    setApiError('')
    setSuccessMessage('')

    try {
      if (editingBudgetId) {
        await saveBudgetUpdate(editingBudgetId, { amount })
        setSuccessMessage('Budget updated successfully!')
      } else {
        await createBudget({
          category: budgetCategory,
          amount
        })
        setSuccessMessage('Budget saved successfully!')
      }

      setShowBudgetForm(false)
      setEditingBudgetId(null)
      setBudgetAmount('')

      await loadBudgets()
    } catch (error) {
      console.error('Budget save error:', error)
      setApiError(error.message || 'Unable to save budget.')
    } finally {
      setSavingBudget(false)
    }
  }

  const editBudget = (item) => {
    if (!item) return

    setEditingBudgetId(item.budget_id)
    setBudgetCategory(item.category || item.category_name)
    setBudgetAmount(String(item.amount))
    setApiError('')
    setSuccessMessage('')
    setShowBudgetForm(true)
  }

  const deleteBudget = async (id) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this budget?'
    )

    if (!confirmed) return

    setApiError('')
    setSuccessMessage('')

    try {
      await removeBudget(id)
      setSuccessMessage('Budget deleted successfully!')
      await loadBudgets()
    } catch (error) {
      console.error('Budget delete error:', error)
      setApiError(error.message || 'Unable to delete budget.')
    }
  }

  // ================================
  // CATEGORY RULE FUNCTIONS
  // ================================

  const openRuleForm = () => {
    setEditingRuleId(null)

    setRuleForm({
      rule_name: '',
      category: 'Food & Dining',
      match_field: 'description',
      match_type: 'contains',
      match_value: '',
      priority: 1,
      is_active: true,
      effective_from: new Date().getFullYear() + '-01-01'
    })

    setApiError('')
    setSuccessMessage('')
    setShowRuleForm(true)
  }

  const editRule = (rule) => {
    setEditingRuleId(rule.rule_id)

    setRuleForm({
      rule_name: rule.rule_name || '',
      category: rule.category || rule.category_name || 'Food & Dining',
      match_field: rule.match_field || 'description',
      match_type: rule.match_type || 'contains',
      match_value: rule.match_value || '',
      priority: rule.priority ?? 1,
      is_active: rule.is_active ?? true,
      effective_from: rule.effective_from || new Date().getFullYear() + '-01-01'
    })

    setApiError('')
    setSuccessMessage('')
    setShowRuleForm(true)
  }

  const submitRule = async (e) => {
    e.preventDefault()

    if (!ruleForm.rule_name.trim() || !ruleForm.match_value.trim()) {
      setApiError('Please enter rule name and matching keyword.')
      return
    }

    setSavingRule(true)
    setApiError('')
    setSuccessMessage('')

    const payload = {
      ...ruleForm,
      rule_name: ruleForm.rule_name.trim(),
      match_value: ruleForm.match_value.trim(),
      priority: Number(ruleForm.priority)
    }

    try {
      if (editingRuleId) {
        await updateCategoryRule(editingRuleId, payload)
        setSuccessMessage('Category rule updated successfully!')
      } else {
        await addCategoryRule(payload)
        setSuccessMessage('Category rule created successfully!')
      }

      setShowRuleForm(false)
      setEditingRuleId(null)
      await loadCategoryRules()
    } catch (error) {
      console.error('Rule save error:', error)
      setApiError(error.message || 'Unable to save category rule.')
    } finally {
      setSavingRule(false)
    }
  }

  const toggleRule = async (rule) => {
    setApiError('')
    setSuccessMessage('')

    try {
      await updateCategoryRule(rule.rule_id, {
        rule_name: rule.rule_name,
        category: rule.category || rule.category_name,
        match_field: rule.match_field,
        match_type: rule.match_type,
        match_value: rule.match_value,
        priority: rule.priority,
        is_active: !rule.is_active,
        effective_from: rule.effective_from,
        effective_to: rule.effective_to
      })

      setSuccessMessage(
        `Rule ${!rule.is_active ? 'enabled' : 'disabled'} successfully!`
      )

      await loadCategoryRules()
    } catch (error) {
      console.error('Rule status error:', error)
      setApiError(error.message || 'Unable to update rule status.')
    }
  }

  const removeRule = async (id) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this category rule?'
    )

    if (!confirmed) return

    setApiError('')
    setSuccessMessage('')

    try {
      await deleteCategoryRule(id)
      setSuccessMessage('Category rule deleted successfully!')
      await loadCategoryRules()
    } catch (error) {
      console.error('Rule delete error:', error)
      setApiError(error.message || 'Unable to delete category rule.')
    }
  }

  // ================================
  // CALCULATIONS
  // ================================

  
  // ================================
  // CALCULATIONS
  // ================================

  const getAmount = (item) => {
  return Number(item.amount) || 0
}

  // Get current local date
  const today = new Date()
  const todayString = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, '0'),
    String(today.getDate()).padStart(2, '0')
  ].join('-')

  const currentMonth = todayString.slice(0, 7)
  // Only current month's transactions
  const monthlyTransactions = transactions.filter(item =>
    item.date?.startsWith(currentMonth)
  )

  // Monthly income
  const totalIncome = monthlyTransactions
    .filter(item => item.type === 'Income')
    .reduce((sum, item) => sum + getAmount(item), 0)

  // Gross expenses (excluding transfers)
  const grossExpenses = monthlyTransactions
    .filter(item => item.type === 'Expense')
    .reduce((sum, item) => sum + getAmount(item), 0)

  // Refunds received during this month
  const totalRefunds = monthlyTransactions
    .filter(item => item.type === 'Refund')
    .reduce((sum, item) => sum + getAmount(item), 0)

  // Net expenses after refunds
  const totalExpenses = Math.max(grossExpenses - totalRefunds, 0)

  // Balance after expenses and refunds
  const totalBalance = totalIncome - totalExpenses

  const formatCurrency = (amount) =>
    '₹' + amount.toLocaleString('en-IN', {
      maximumFractionDigits: 2
    })

  const filteredTransactions = transactions.filter(item => {
    const matchesSearch =
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.category.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesCategory =
      selectedCategory === 'All' ||
      item.category === selectedCategory

    const matchesType =
      selectedType === 'All' ||
      item.type === selectedType

    return matchesSearch && matchesCategory && matchesType
  })

  // Show only budgets covering today's date.
  const budgetDetails = budgets
    .filter(item =>
      item.period_start <= todayString &&
      item.period_end >= todayString
    )
    .map(item => {
      const category = item.category || item.category_name || 'Other'
      const limit = Number(item.amount) || 0

      const spent = transactions
        .filter(transaction =>
          transaction.category === category &&
          transaction.type === 'Expense' &&
          transaction.date >= item.period_start &&
          transaction.date <= item.period_end
        )
        .reduce((sum, transaction) => sum + getAmount(transaction), 0)

      const percentage = limit > 0
        ? Math.round((spent / limit) * 100)
        : 0

      return {
        id: item.budget_id,
        category,
        limit,
        spent,
        percentage,
        remaining: limit - spent
      }
    })

  const stats = [
    {
      title: 'Total Balance',
      amount: formatCurrency(totalBalance),
      change: 'Live',
      icon: Wallet,
      color: 'purple'
    },
    {
      title: 'Monthly Income',
      amount: formatCurrency(totalIncome),
      change: 'Live',
      icon: TrendingUp,
      color: 'green'
    },
    {
      title: 'Monthly Expenses',
      amount: formatCurrency(totalExpenses),
      change: 'Live',
      icon: TrendingDown,
      color: 'orange'
    },
    {
      title: 'Total Savings',
      amount: formatCurrency(totalBalance),
      change: 'Live',
      icon: PiggyBank,
      color: 'blue'
    }
  ]

  // ================================
  // UI
  // ================================

  return (
    <>
      {/* BUDGET FORM */}
      {showBudgetForm && (
        <div className="modal-overlay">
          <form className="transaction-form" onSubmit={submitBudget}>
            <h2>
              {editingBudgetId ? 'Edit Monthly Budget' : 'Set Monthly Budget'}
            </h2>

            <p>Choose a category and set your spending limit.</p>

            <label>Category</label>
            <select
              value={budgetCategory}
              onChange={e => setBudgetCategory(e.target.value)}
              disabled={Boolean(editingBudgetId)}
            >
              <option>Food & Dining</option>
              <option>Transportation</option>
              <option>Shopping</option>
              <option>Housing</option>
              <option>Entertainment</option>
            </select>

            <label>Budget Amount (₹)</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="Enter budget amount"
              value={budgetAmount}
              onChange={e => setBudgetAmount(e.target.value)}
              required
            />

            <div className="form-actions">
              <button
                type="button"
                onClick={() => {
                  setShowBudgetForm(false)
                  setEditingBudgetId(null)
                  setBudgetAmount('')
                }}
                disabled={savingBudget}
              >
                Cancel
              </button>

              <button type="submit" disabled={savingBudget}>
                {savingBudget
                  ? 'Saving...'
                  : editingBudgetId ? 'Update Budget' : 'Save Budget'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* CATEGORY RULE FORM */}
      {showRuleForm && (
        <div className="modal-overlay">
          <form className="transaction-form" onSubmit={submitRule}>
            <h2>
              {editingRuleId ? 'Edit Category Rule' : 'Create Category Rule'}
            </h2>

            <p>Automatically categorize transactions using matching rules.</p>

            <label>Rule Name</label>
            <input
              value={ruleForm.rule_name}
              onChange={e => setRuleForm({
                ...ruleForm,
                rule_name: e.target.value
              })}
              placeholder="e.g. Swiggy Food Rule"
              required
            />

            <label>Category</label>
            <select
              value={ruleForm.category}
              onChange={e => setRuleForm({
                ...ruleForm,
                category: e.target.value
              })}
            >
              <option>Food & Dining</option>
              <option>Transportation</option>
              <option>Shopping</option>
              <option>Housing</option>
              <option>Entertainment</option>
            </select>

            <label>Match Field</label>
            <select
              value={ruleForm.match_field}
              onChange={e => setRuleForm({
                ...ruleForm,
                match_field: e.target.value
              })}
            >
              <option value="description">Transaction Description</option>
              <option value="merchant">Merchant Name</option>
            </select>

            <label>Match Type</label>
            <select
              value={ruleForm.match_type}
              onChange={e => setRuleForm({
                ...ruleForm,
                match_type: e.target.value
              })}
            >
              <option value="contains">Contains</option>
              <option value="exact">Exact Match</option>
              <option value="starts_with">Starts With</option>
            </select>

            <label>Matching Keyword</label>
            <input
              value={ruleForm.match_value}
              onChange={e => setRuleForm({
                ...ruleForm,
                match_value: e.target.value
              })}
              placeholder="e.g. swiggy"
              required
            />

            <label>Priority (Lower number = Higher priority)</label>
            <input
              type="number"
              min="1"
              value={ruleForm.priority}
              onChange={e => setRuleForm({
                ...ruleForm,
                priority: e.target.value
              })}
              required
            />

            <label>Effective From</label>
            <input
              type="date"
              value={ruleForm.effective_from}
              onChange={e => setRuleForm({
                ...ruleForm,
                effective_from: e.target.value
              })}
              required
            />

            <label className="rule-checkbox">
              <input
                type="checkbox"
                checked={ruleForm.is_active}
                onChange={e => setRuleForm({
                  ...ruleForm,
                  is_active: e.target.checked
                })}
              />
              Rule is active
            </label>

            <div className="form-actions">
              <button
                type="button"
                onClick={() => setShowRuleForm(false)}
                disabled={savingRule}
              >
                Cancel
              </button>

              <button type="submit" disabled={savingRule}>
                {savingRule
                  ? 'Saving...'
                  : editingRuleId ? 'Update Rule' : 'Save Rule'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TRANSACTION FORM */}
      {showForm && (
        <div className="modal-overlay">
          <form className="transaction-form" onSubmit={submitTransaction}>
            <h2>
              {editId ? 'Edit Transaction' : 'Add Transaction'}
            </h2>

            <p>Enter your income or expense details.</p>

            <label>Transaction Name</label>
            <input
              type="text"
              placeholder="e.g. Swiggy food order"
              value={formData.name}
              onChange={e => setFormData({
                ...formData,
                name: e.target.value
              })}
              required
            />

            <label>Amount (₹)</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="Enter amount"
              value={formData.amount}
              onChange={e => setFormData({
                ...formData,
                amount: e.target.value
              })}
              required
            />

            <label>Type</label>
            <select
              value={formData.type}
              onChange={e => setFormData({
                ...formData,
                type: e.target.value
              })}
            >
              <option>Expense</option>
              <option>Income</option>
            </select>

            <label>Category</label>
            <select
              value={formData.category}
              onChange={e => setFormData({
                ...formData,
                category: e.target.value
              })}
            >
              <option value="">⚡ Auto Detect</option>
              <option>Food & Dining</option>
              <option>Transportation</option>
              <option>Shopping</option>
              <option>Housing</option>
              <option>Entertainment</option>
              <option>Income</option>
            </select>

            <p className="form-hint">
              Select Auto Detect to use your saved category rules.
            </p>

            <label>Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={e => setFormData({
                ...formData,
                date: e.target.value
              })}
              required
            />

            <div className="form-actions">
              <button
                type="button"
                onClick={closeTransactionForm}
                disabled={savingTransaction}
              >
                Cancel
              </button>

              <button type="submit" disabled={savingTransaction}>
                {savingTransaction
                  ? 'Saving...'
                  : editId ? 'Update Transaction' : 'Save Transaction'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="app">

        {/* SIDEBAR */}
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-icon">
              <Wallet size={23} />
            </div>

            <span>
              Penny<span className="brand-light">Wise</span>
            </span>
          </div>

          <p className="menu-label">MAIN MENU</p>

          <nav>
            <a href="#dashboard-section" className="nav-item active">
              <LayoutDashboard size={19} />
              Dashboard
            </a>

            <a href="#transactions-section" className="nav-item">
              <Receipt size={19} />
              Transactions
            </a>

            <a href="#recurring-section" className="nav-item">
              <Repeat size={19} />
              Recurring Payments
            </a>
            <a href="#insights-section" className="nav-item">
  <ShieldAlert size={19} />
  Insights
</a>

            <a href="#budgets-section" className="nav-item">
              <Target size={19} />
              Budgets
            </a>

            <a href="#rules-section" className="nav-item">
              <Tags size={19} />
              Category Rules
            </a>
          </nav>

          <p className="menu-label second-label">PREFERENCES</p>

          <nav>
            <a href="#" className="nav-item">
              <Settings size={19} />
              Settings
            </a>
          </nav>

          <div className="sidebar-bottom">
            <div className="avatar">B</div>
            <div>
              <strong>Bhargavi</strong>
              <small>Personal Account</small>
            </div>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main className="main">

          {/* TOPBAR */}
          <header className="topbar" id="dashboard-section">
            <div>
              <h2>Dashboard</h2>
              <p>Welcome back! Here's your financial overview.</p>
            </div>

            <div className="top-actions">
              <button
                className="add-btn"
                onClick={() => {
                  closeTransactionForm()
                  setApiError('')
                  setSuccessMessage('')
                  setShowForm(true)
                }}
              >
                + Add Transaction
              </button>

              <button className="icon-btn notification">
                <Bell size={19} />
              </button>

              <div className="avatar top-avatar">B</div>
            </div>
          </header>

          {/* API MESSAGES */}
          {apiError && (
            <p className="empty-message" role="alert">
              {apiError}
            </p>
          )}

          {successMessage && (
            <p className="success-message" role="status">
              {successMessage}
            </p>
          )}

          {/* WELCOME SECTION */}
          <section className="welcome">
            <div>
              <span className="welcome-tag">YOUR FINANCIAL SPACE</span>

              <h1>
                Make your money<br />
                work <span>smarter.</span>
              </h1>

              <p>
                Track spending, manage budgets and build better habits.
              </p>
            </div>

            <div className="welcome-art">
              <PiggyBank size={112} strokeWidth={1.1} />
            </div>
          </section>

          {/* STATISTICS */}
          <section className="stats-grid">
            {stats.map((item, index) => {
              const Icon = item.icon

              return (
                <motion.div
                  className="stat-card"
                  key={item.title}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.12 }}
                  whileHover={{ y: -5 }}
                >
                  <div className="stat-top">
                    <div className={`stat-icon ${item.color}`}>
                      <Icon size={21} />
                    </div>

                    <span className="trend">
                      <ArrowUpRight size={14} />
                      {item.change}
                    </span>
                  </div>

                  <p>{item.title}</p>
                  <h2>{item.amount}</h2>
                </motion.div>
              )
            })}
          </section>

          {/* SPENDING ANALYTICS */}
         <SpendingCharts transactions={monthlyTransactions} />

          {/* CATEGORY RULES */}
          <section className="panel rules-panel" id="rules-section">
            <div className="panel-heading">
              <div>
                <h3><Tags size={19} /> Category Rules</h3>
                <p>Automatically organize transactions using matching keywords.</p>
              </div>

              <button className="add-btn" onClick={openRuleForm}>
                <Plus size={16} /> Add Rule
              </button>
            </div>

            {loadingRules ? (
              <p className="empty-message">Loading category rules...</p>
            ) : categoryRules.length === 0 ? (
              <p className="empty-message">
                No category rules yet. Add a rule to automatically categorize transactions.
              </p>
            ) : (
              categoryRules.map(rule => (
                <div className="rule-row" key={rule.rule_id}>
                  <div className="rule-icon">
                    <Zap size={19} />
                  </div>

                  <div className="rule-info">
                    <strong>{rule.rule_name}</strong>

                    <small>
                      {rule.match_field} {rule.match_type} "{rule.match_value}"
                    </small>

                    <small>
                      Category: {rule.category || rule.category_name}
                      {' · '}Priority: {rule.priority}
                    </small>
                  </div>

                  <div className="rule-actions">
                    <span className={rule.is_active ? 'rule-active' : 'rule-inactive'}>
                      {rule.is_active ? 'Active' : 'Inactive'}
                    </span>

                    <button
                      className="edit-btn"
                      onClick={() => editRule(rule)}
                    >
                      <Pencil size={14} /> Edit
                    </button>

                    <button
                      className="edit-btn"
                      onClick={() => toggleRule(rule)}
                    >
                      {rule.is_active ? 'Disable' : 'Enable'}
                    </button>

                    <button
                      className="delete-btn"
                      onClick={() => removeRule(rule.rule_id)}
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </section>

        {/* SMART INSIGHTS */}
        <section className="panel insights-panel" id="insights-section">
          <div className="panel-heading">
            <div>
              <h3>
                <ShieldAlert size={19} /> Smart Insights
              </h3>
              <p>Understand unusual spending and important payment alerts.</p>
            </div>

            <button
              className="add-btn"
              onClick={handleGenerateInsights}
              disabled={generatingInsights}
            >
              <RefreshCw
                size={16}
                className={generatingInsights ? 'spin' : ''}
              />
              {generatingInsights ? 'Generating...' : 'Generate Insights'}
            </button>
          </div>

          {!loadingInsights && (
            <div className="insight-summary">
              <div>
                <strong>{insights.length}</strong>
                <span>Total Insights</span>
              </div>
              <div>
                <strong>
                  {insights.filter(item => item.severity === 'High').length}
                </strong>
                <span>High Priority</span>
              </div>
              <div>
                <strong>
                  {insights.filter(item => item.status === 'New').length}
                </strong>
                <span>New Alerts</span>
              </div>
            </div>
          )}

          {loadingInsights ? (
            <p className="empty-message">Loading smart insights...</p>
          ) : insights.length === 0 ? (
            <div className="insight-empty">
              <ShieldAlert size={38} />
              <strong>No insights available yet</strong>
              <p>Generate insights to discover spending patterns and alerts.</p>
            </div>
          ) : (
            <div className="insight-list">
              {insights.map(item => {
                const severityClass = item.severity.toLowerCase()

                return (
                  <motion.div
                    className={`insight-card ${severityClass}`}
                    key={item.insight_id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="insight-icon">
                      {item.severity === 'High' ? (
                        <AlertTriangle size={21} />
                      ) : item.severity === 'Medium' ? (
                        <Info size={21} />
                      ) : (
                        <Bell size={21} />
                      )}
                    </div>

                    <div className="insight-content">
                      <div className="insight-title-row">
                        <strong>{item.title}</strong>
                        <span className={`severity-badge ${severityClass}`}>
                          {item.severity}
                        </span>
                      </div>

                      <p>{item.description}</p>

                      <div className="insight-meta">
                        <span>{item.insight_type}</span>
                        {item.category && <span>{item.category}</span>}
                        <span>
                          {new Date(item.created_at).toLocaleDateString('en-IN')}
                        </span>
                      </div>

                      <div className="insight-footer">
                        <span className={`insight-status ${item.status.toLowerCase()}`}>
                          {item.status}
                        </span>

                        <div className="insight-actions">
                          {item.status === 'New' && (
                            <button
                              className="edit-btn"
                              disabled={updatingInsightId === item.insight_id}
                              onClick={() => handleInsightStatus(
                                item.insight_id,
                                'Acknowledged'
                              )}
                            >
                              Acknowledge
                            </button>
                          )}

                          {item.status !== 'Resolved' && (
                            <button
                              className="edit-btn"
                              disabled={updatingInsightId === item.insight_id}
                              onClick={() => handleInsightStatus(
                                item.insight_id,
                                'Resolved'
                              )}
                            >
                              <CheckCircle2 size={14} /> Resolve
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </section>

          {/* RECURRING PAYMENTS */}
          <div id="recurring-section">
            <RecurringPayments transactions={transactions} />
          </div>

          {/* TRANSACTIONS AND BUDGET */}
          <section className="content-grid">

            {/* TRANSACTIONS PANEL */}
            <div className="panel transactions" id="transactions-section">
              <div className="panel-heading">
                <div>
                  <h3>Recent Transactions</h3>
                  <p>Your latest money activity</p>
                </div>

                <a href="#transactions-section" className="view-btn">
                  View all <ArrowUpRight size={15} />
                </a>
              </div>

              <div className="transaction-search">
                <Search size={18} />

                <input
                  type="text"
                  placeholder="Search transactions..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
              </div>

              <div className="transaction-filters">
                <select
                  value={selectedCategory}
                  onChange={e => setSelectedCategory(e.target.value)}
                >
                  <option value="All">All Categories</option>
                  <option value="Food & Dining">Food & Dining</option>
                  <option value="Transportation">Transportation</option>
                  <option value="Shopping">Shopping</option>
                  <option value="Housing">Housing</option>
                  <option value="Entertainment">Entertainment</option>
                  <option value="Income">Income</option>
                </select>

                <select
                  value={selectedType}
                  onChange={e => setSelectedType(e.target.value)}
                >
                  <option value="All">All Transactions</option>
                  <option value="Income">Income Only</option>
                  <option value="Expense">Expenses Only</option>
                </select>
              </div>

              {loadingTransactions ? (
                <p className="empty-message">
                  Loading transactions from database...
                </p>
              ) : transactions.length === 0 ? (
                <p className="empty-message">No transactions found.</p>
              ) : filteredTransactions.length === 0 ? (
                <p className="empty-message">No transactions match your filters.</p>
              ) : (
                filteredTransactions.map(item => {
                  const Icon = item.icon

                  return (
                    <motion.div
                      className="transaction-row"
                      key={item.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                    >
                      <div className={`transaction-icon ${item.color}`}>
                        <Icon size={19} />
                      </div>

                      <div className="transaction-info">
                        <strong>{item.name}</strong>
                        <small>{item.category} · {item.date}</small>
                      </div>

                      <div className="transaction-actions">
                       <strong
  className={
    item.type === 'Income' || item.type === 'Refund'
      ? 'positive'
      : 'negative'
  }
>
  {item.type === 'Income' || item.type === 'Refund' ? '+' : '-'}
  ₹{Number(item.amount).toLocaleString('en-IN')}
</strong>

                        <button
                          className="edit-btn"
                          onClick={() => editTransaction(item.id)}
                        >
                          Edit
                        </button>

                        <button
                          className="delete-btn"
                          onClick={() => deleteTransaction(item.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </motion.div>
                  )
                })
              )}
            </div>

            {/* BUDGET PANEL */}
            <div className="panel budget" id="budgets-section">
              <div className="panel-heading">
                <div>
                  <h3>Monthly Budget</h3>
                  <p>Your category-wise spending</p>
                </div>

                <button className="add-btn" onClick={openBudgetForm}>
                  + Set Budget
                </button>
              </div>

              {loadingBudgets ? (
                <p className="empty-message">Loading budgets...</p>
              ) : budgetDetails.length === 0 ? (
                <p className="empty-message">
                  No budgets found. Click Set Budget to create your first budget.
                </p>
              ) : (
                budgetDetails.map(item => (
                  <div className="budget-category" key={item.id}>
                    <div className="budget-category-heading">
                      <strong>{item.category}</strong>

                      <span>
                        ₹{item.spent.toLocaleString('en-IN')} /
                        {' '}₹{item.limit.toLocaleString('en-IN')}
                      </span>
                    </div>

                    <div className="progress">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${Math.min(item.percentage, 100)}%`,
                          background: item.percentage > 100
                            ? '#ef4444'
                            : '#8055e8'
                        }}
                      />
                    </div>

                    <div className="budget-footer">
                      <span>{item.percentage}% used</span>

                      <strong>
                        {item.remaining >= 0
                          ? `₹${item.remaining.toLocaleString('en-IN')} left`
                          : `₹${Math.abs(item.remaining).toLocaleString('en-IN')} exceeded`}
                      </strong>
                    </div>

                    {item.percentage > 100 && (
                      <p className="budget-warning">
                        ⚠️ Budget exceeded!
                      </p>
                    )}

                    <div className="transaction-actions">
                      <button
                        className="edit-btn"
                        onClick={() => {
                          const originalBudget = budgets.find(
                            budget => budget.budget_id === item.id
                          )
                          editBudget(originalBudget)
                        }}
                      >
                        Edit
                      </button>

                      <button
                        className="delete-btn"
                        onClick={() => deleteBudget(item.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          {/* FOOTER */}
          <footer>
            © 2026 PennyWise · Smart money, smarter life.
          </footer>

        </main>
      </div>
    </>
  )
}

export default App
