
const API_BASE_URL = "http://127.0.0.1:5000";

// Common API response handler
async function handleResponse(response) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "API request failed");
  }

  return data;
}

// ================================
// TRANSACTION APIs
// ================================

export async function getTransactions() {
  const response = await fetch(`${API_BASE_URL}/api/transactions`);
  return handleResponse(response);
}

export async function addTransaction(transaction) {
  const response = await fetch(`${API_BASE_URL}/api/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transaction)
  });
  return handleResponse(response);
}

export async function updateTransaction(id, transaction) {
  const response = await fetch(`${API_BASE_URL}/api/transactions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transaction)
  });
  return handleResponse(response);
}

export async function deleteTransaction(id) {
  const response = await fetch(`${API_BASE_URL}/api/transactions/${id}`, {
    method: "DELETE"
  });
  return handleResponse(response);
}

// ================================
// DASHBOARD & CATEGORY APIs
// ================================

export async function getDashboard() {
  const response = await fetch(`${API_BASE_URL}/api/dashboard`);
  return handleResponse(response);
}

export async function getCategories() {
  const response = await fetch(`${API_BASE_URL}/api/categories`);
  return handleResponse(response);
}

// ================================
// BUDGET APIs
// ================================

export async function getBudgets() {
  const response = await fetch(`${API_BASE_URL}/api/budgets`);
  return handleResponse(response);
}

export async function addBudget(budget) {
  const response = await fetch(`${API_BASE_URL}/api/budgets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(budget)
  });
  return handleResponse(response);
}

export async function updateBudget(id, budget) {
  const response = await fetch(`${API_BASE_URL}/api/budgets/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(budget)
  });
  return handleResponse(response);
}

export async function deleteBudget(id) {
  const response = await fetch(`${API_BASE_URL}/api/budgets/${id}`, {
    method: "DELETE"
  });
  return handleResponse(response);
}

// ================================
// CATEGORY RULE APIs
// ================================

// GET all category rules
export async function getCategoryRules() {
  const response = await fetch(`${API_BASE_URL}/api/category-rules`);
  return handleResponse(response);
}

// ADD category rule
export async function addCategoryRule(rule) {
  const response = await fetch(`${API_BASE_URL}/api/category-rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rule)
  });
  return handleResponse(response);
}

// UPDATE category rule
export async function updateCategoryRule(id, rule) {
  const response = await fetch(`${API_BASE_URL}/api/category-rules/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rule)
  });
  return handleResponse(response);
}

// DELETE category rule
export async function deleteCategoryRule(id) {
  const response = await fetch(`${API_BASE_URL}/api/category-rules/${id}`, {
    method: "DELETE"
  });
  return handleResponse(response);
}


// ================================
// INSIGHTS APIs
// ================================

// Generate and save insights
export async function generateInsights() {
  const response = await fetch(`${API_BASE_URL}/api/insights/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });

  return handleResponse(response);
}

// Get all saved insights
export async function getInsights() {
  const response = await fetch(`${API_BASE_URL}/api/insights`);
  return handleResponse(response);
}

// Update insight status
export async function updateInsight(id, status) {
  const response = await fetch(`${API_BASE_URL}/api/insights/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status })
  });

  return handleResponse(response);
}

// ================================
// CATEGORIZATION HISTORY API
// ================================

export async function getCategorizationHistory() {
  const response = await fetch(`${API_BASE_URL}/api/categorization-history`);
  return handleResponse(response);
}
