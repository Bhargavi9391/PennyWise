
import { useState, useEffect, useCallback } from 'react'
import {
  Repeat,
  CalendarDays,
  Clock,
  Plus,
  X,
  Pencil,
  Trash2,
  RefreshCw
} from 'lucide-react'

import './RecurringPayments.css'

const API_URL = 'http://127.0.0.1:5000/api'

function RecurringPayments({ transactions = [] }) {
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState(null)

  const [payments, setPayments] = useState(() => {
    try {
      const saved = localStorage.getItem('pennywiseRecurringPayments')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  const [detectedPayments, setDetectedPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [detecting, setDetecting] = useState(false)
  const [apiError, setApiError] = useState('')

  const emptyForm = {
    name: '',
    amount: '',
    category: 'Entertainment',
    frequency: 'Monthly',
    nextDate: ''
  }

  const [formData, setFormData] = useState(emptyForm)

  // Save manually added payments
  useEffect(() => {
    localStorage.setItem(
      'pennywiseRecurringPayments',
      JSON.stringify(payments)
    )
  }, [payments])

  // Load recurring payments from backend
  const loadRecurringPayments = useCallback(async () => {
    try {
      setLoading(true)
      setApiError('')

      const response = await fetch(`${API_URL}/recurring`)

      if (!response.ok) {
        throw new Error('Unable to load recurring payments')
      }

      const data = await response.json()

      const records = Array.isArray(data)
        ? data
        : data.recurring_payments || []

      setDetectedPayments(
        records.map((item, index) => ({
          id: item.series_id || item.id || index,
          name:
            item.series_name ||
            item.name ||
            item.description ||
            'Recurring Payment',
          amount: Number(
            item.expected_amount ?? item.amount ?? 0
          ),
          category: item.category || 'Other',
          frequency: item.frequency || 'Monthly',
          nextDate:
            item.next_payment_date ||
            item.nextDate ||
            '',
          count: Number(
            item.occurrence_count ??
            item.payment_count ??
            item.history?.length ??
            0
          ),
        status: item.status || 'Active',
paymentStatus: item.payment_status || 'Upcoming',
daysOverdue: item.days_overdue || 0,
dueDate: item.due_date || '',
history: item.history || []
        }))
      )
    } catch (error) {
      console.error('Recurring API error:', error)
      setApiError(
        'Could not connect to the backend. Please check whether the backend is running.'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRecurringPayments()
  }, [loadRecurringPayments])

  // Run automatic recurring detection
  const detectRecurringPayments = async () => {
    try {
      setDetecting(true)
      setApiError('')

      const response = await fetch(
        `${API_URL}/recurring/detect`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({})
        }
      )

      if (!response.ok) {
        throw new Error('Recurring detection failed')
      }

      const result = await response.json()

      await loadRecurringPayments()

      window.alert(
        `Detection completed! ${result.detected_count ?? 0} recurring payment(s) detected.`
      )
    } catch (error) {
      console.error('Detection error:', error)
      setApiError(
        'Recurring detection failed. Please check the backend.'
      )
    } finally {
      setDetecting(false)
    }
  }

  const openAddForm = () => {
    setEditId(null)
    setFormData({ ...emptyForm })
    setShowForm(true)
  }

  const openEditForm = (item) => {
    setEditId(item.id)

    setFormData({
      name: item.name,
      amount: String(item.amount),
      category: item.category,
      frequency: item.frequency,
      nextDate: item.nextDate
    })

    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditId(null)
    setFormData({ ...emptyForm })
  }

  // Save manual payment
  const savePayment = (e) => {
    e.preventDefault()

    const paymentData = {
      name: formData.name.trim(),
      amount: Number(formData.amount),
      category: formData.category,
      frequency: formData.frequency,
      nextDate: formData.nextDate
    }

    if (!paymentData.name || paymentData.amount <= 0) {
      return
    }

    if (editId !== null) {
      setPayments(prev =>
        prev.map(item =>
          item.id === editId
            ? { ...item, ...paymentData }
            : item
        )
      )
    } else {
      setPayments(prev => [
        ...prev,
        {
          id: Date.now(),
          ...paymentData
        }
      ])
    }

    closeForm()
  }

  const deletePayment = (id) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this payment?'
    )

    if (confirmed) {
      setPayments(prev =>
        prev.filter(item => item.id !== id)
      )
    }
  }

  const formatCurrency = amount =>
    `₹${Number(amount || 0).toLocaleString('en-IN')}`

  const totalManual = payments.reduce(
    (sum, item) => sum + Number(item.amount || 0),
    0
  )

  const totalDetected = detectedPayments.reduce(
    (sum, item) => sum + Number(item.amount || 0),
    0
  )

  const totalRecurring = totalManual + totalDetected

  return (
    <section className="recurring-section">

      {/* Heading */}
      <div className="recurring-heading">
        <div>
          <span className="recurring-tag">
            SMART PAYMENT TRACKER
          </span>

          <h2>Recurring Payments</h2>

          <p>
            Manage your regular monthly payments.
          </p>
        </div>

        <div className="recurring-total">
          <Repeat size={20} />

          <span>Estimated recurring total</span>

          <strong>{formatCurrency(totalRecurring)}</strong>
        </div>
      </div>

      {/* Actions */}
      <div className="recurring-actions">
        <button
          className="recurring-add-btn"
          onClick={openAddForm}
          type="button"
        >
          <Plus size={18} />
          Add Payment
        </button>

        <button
          className="recurring-add-btn"
          onClick={detectRecurringPayments}
          type="button"
          disabled={detecting}
        >
          <RefreshCw
            size={17}
            className={detecting ? 'spinning' : ''}
          />
          {detecting ? 'Detecting...' : 'Detect Now'}
        </button>
      </div>

      {/* API Error */}
      {apiError && (
        <div className="recurring-note">
          <span>{apiError}</span>
          <button
            type="button"
            onClick={loadRecurringPayments}
          >
            Retry
          </button>
        </div>
      )}

      {/* Add / Edit Form */}
      {showForm && (
        <div className="recurring-modal-overlay">
          <form
            className="recurring-form"
            onSubmit={savePayment}
          >
            <div className="recurring-form-heading">
              <div>
                <h2>
                  {editId !== null
                    ? 'Edit Recurring Payment'
                    : 'Add Recurring Payment'}
                </h2>

                <p>Enter your regular payment details.</p>
              </div>

              <button
                type="button"
                className="recurring-close-btn"
                onClick={closeForm}
              >
                <X size={20} />
              </button>
            </div>

            <label>Payment Name</label>
            <input
              type="text"
              placeholder="e.g. Netflix, House Rent"
              value={formData.name}
              onChange={e =>
                setFormData({
                  ...formData,
                  name: e.target.value
                })
              }
              required
            />

            <label>Amount (₹)</label>
            <input
              type="number"
              min="1"
              placeholder="Enter payment amount"
              value={formData.amount}
              onChange={e =>
                setFormData({
                  ...formData,
                  amount: e.target.value
                })
              }
              required
            />

            <label>Category</label>
            <select
              value={formData.category}
              onChange={e =>
                setFormData({
                  ...formData,
                  category: e.target.value
                })
              }
            >
              <option>Entertainment</option>
              <option>Housing</option>
              <option>Food & Dining</option>
              <option>Transportation</option>
              <option>Shopping</option>
              <option>Other</option>
            </select>

            <label>Payment Frequency</label>
            <select
              value={formData.frequency}
              onChange={e =>
                setFormData({
                  ...formData,
                  frequency: e.target.value
                })
              }
            >
              <option>Monthly</option>
              <option>Weekly</option>
              <option>Quarterly</option>
              <option>Yearly</option>
            </select>

            <label>Next Payment Date</label>
            <input
              type="date"
              value={formData.nextDate}
              onChange={e =>
                setFormData({
                  ...formData,
                  nextDate: e.target.value
                })
              }
              required
            />

            <div className="recurring-form-actions">
              <button
                type="button"
                onClick={closeForm}
              >
                Cancel
              </button>

              <button type="submit">
                {editId !== null
                  ? 'Update Payment'
                  : 'Save Payment'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="recurring-empty">
          <RefreshCw size={22} />
          <p>Loading recurring payments...</p>
        </div>
      )}

      {/* Manually Added Payments */}
      {!loading && payments.length > 0 && (
        <div className="recurring-list">
          {payments.map(item => (
            <div className="recurring-card" key={item.id}>
              <div className="recurring-icon">
                <Repeat size={22} />
              </div>

              <div className="recurring-info">
                <strong>{item.name}</strong>
                <span>{item.category}</span>

                <small>
                  <CalendarDays size={13} />
                  Next payment: {item.nextDate}
                </small>
              </div>

              <div className="recurring-amount">
                <strong>{formatCurrency(item.amount)}</strong>
                <span>{item.frequency} payment</span>
                {item.dueDate && (
  <small>Due date: {item.dueDate}</small>
)}

{item.nextDate && (
  <small>Next scheduled: {item.nextDate}</small>
)}
              </div>

              <div className="recurring-card-actions">
                <button
                  className="recurring-edit-btn"
                  onClick={() => openEditForm(item)}
                  type="button"
                >
                  <Pencil size={15} />
                  Edit
                </button>

                <button
                  className="recurring-delete-btn"
                  onClick={() => deletePayment(item.id)}
                  type="button"
                >
                  <Trash2 size={15} />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Backend Detected Payments */}
      {!loading && detectedPayments.length > 0 && (
        <>
          <div className="recurring-subheading">
            <h3>Automatically Detected Payments</h3>
            <span>{detectedPayments.length} detected</span>
          </div>

          <div className="recurring-list">
            {detectedPayments.map(item => (
              <div
                className="recurring-card"
                key={item.id}
              >
                <div className="recurring-icon">
                  <Repeat size={22} />
                </div>

                <div className="recurring-info">
                  <strong>{item.name}</strong>
                  <span>{item.category}</span>

                  <small>
                    <CalendarDays size={13} />
                    {item.count} payment records found
                  </small>

                  {item.nextDate && (
                    <small>
                      <Clock size={13} />
                      Next payment: {item.nextDate}
                    </small>
                  )}
                </div>

                <div className="recurring-amount">
                  <strong>
                    {formatCurrency(item.amount)}
                  </strong>

                  <span>{item.frequency} · Detected</span>
                  <small>
  Account status: {item.status}
</small>

<small
  style={{
    color: item.paymentStatus === 'Overdue'
      ? '#dc2626'
      : '#16a34a',
    fontWeight: 600
  }}
>
  Payment status: {item.paymentStatus}
</small>

{item.paymentStatus === 'Overdue' && (
  <small style={{ color: '#dc2626' }}>
    {item.daysOverdue} days overdue
  </small>
)}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Empty State */}
      {!loading &&
        payments.length === 0 &&
        detectedPayments.length === 0 && (
          <div className="recurring-empty">
            <div className="recurring-empty-icon">
              <Repeat size={30} />
            </div>

            <h3>No recurring payments found</h3>

            <p>
              Add your regular bills or click Detect Now
              to identify recurring transactions automatically.
            </p>
          </div>
        )}

      {/* Note */}
      <div className="recurring-note">
        <Clock size={16} />

        <span>
          Manually added payments and automatically detected
          transactions are shown separately.
        </span>
      </div>

    </section>
  )
}

export default RecurringPayments
