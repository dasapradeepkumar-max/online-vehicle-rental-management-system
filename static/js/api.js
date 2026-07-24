// API.JS - API CALLS AND HELPERS

const API_BASE = '/api/public';

// Fetch vehicles with error handling
async function fetchVehicles() {
  try {
    const response = await fetch(`${API_BASE}/vehicles`);
    if (!response.ok) throw new Error('Failed to fetch vehicles');
    return await response.json();
  } catch (error) {
    console.error('Error fetching vehicles:', error);
    return [];
  }
}

// Fetch stats with error handling
async function fetchStats() {
  try {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    return await response.json();
  } catch (error) {
    console.error('Error fetching stats:', error);
    return {
      total_vehicles: 0,
      available: 0,
      active_rentals: 0
    };
  }
}

// Update available count with animation
function updateAvailableCount(count) {
  const element = document.getElementById('availableVehicles');
  if (element) {
    element.style.animation = 'none';
    setTimeout(() => {
      element.textContent = count;
      element.style.animation = 'countUp 0.6s ease';
    }, 10);
  }
}

// Update active rentals with animation
function updateActiveRentals(count) {
  const element = document.getElementById('activeRentals');
  if (element) {
    element.style.animation = 'none';
    setTimeout(() => {
      element.textContent = count;
      element.style.animation = 'countUp 0.6s ease';
    }, 10);
  }
}

// Format price with Indian rupee
function formatPrice(price) {
  return `₹${price.toLocaleString('en-IN')}`;
}

// API error handler
function handleApiError(error) {
  console.error('API Error:', error);
  // Show toast notification (if available)
  if (typeof showToast === 'function') {
    showToast('Error loading data. Please refresh.', 'error');
  }
}
