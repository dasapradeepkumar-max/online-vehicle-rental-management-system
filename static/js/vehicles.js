/* ════════════════════════════════════════════════════════════
   vehicles.js — VehicleHub Real-Time Browser
   ════════════════════════════════════════════════════════════ */

class VehiclePage {
  constructor() {
    this.allVehicles = [];
    this.filteredVehicles = [];
    this.filters = {
      type: 'all',
      avail: 'available',
      maxPrice: 5000,
      search: '',
      location: ''
    };
    this.socket = io();
    this.init();
  }

  async init() {
    await this.loadVehicles();
    this.setupSocket();
  }

  async loadVehicles() {
    const grid = document.getElementById('vGrid');
    try {
      const res = await fetch('/api/vehicles');
      if (!res.ok) throw new Error('API Error');
      this.allVehicles = await res.json();
      this.applyFilters();
    } catch (e) {
      console.error('Failed to load vehicles:', e);
      if (grid) grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:60px;color:var(--text-muted);">
          <i class="fas fa-exclamation-circle" style="font-size:40px;margin-bottom:16px;display:block;"></i>
          <h3>Unable to load vehicles</h3>
          <p>Please check your connection and refresh.</p>
        </div>`;
    }
  }

  setFilter(field, value, btn) {
    this.filters[field] = value;
    if (btn) {
      btn.parentElement.querySelectorAll('.sb-tab').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
    }
    this.applyFilters();
  }

  updatePrice(val) {
    this.filters.maxPrice = parseInt(val);
    const label = document.getElementById('priceLabel');
    if (label) label.textContent = '₹' + this.filters.maxPrice.toLocaleString('en-IN');
    this.applyFilters();
  }

  applyFilters() {
    const sInput = document.getElementById('searchInput');
    const lInput = document.getElementById('locationFilter');

    this.filters.search = sInput ? sInput.value.toLowerCase() : '';
    this.filters.location = lInput ? lInput.value.toLowerCase() : '';

    this.filteredVehicles = this.allVehicles.filter(v => {
      if (v.status !== 'available') return false;
      if (this.filters.type !== 'all' && v.type !== this.filters.type) return false;
      if (this.filters.avail === 'available' && v.status !== 'available') return false;
      if (v.price_per_day > this.filters.maxPrice) return false;
      if (this.filters.search && !v.name.toLowerCase().includes(this.filters.search)) return false;
      if (this.filters.location && !(v.location || '').toLowerCase().includes(this.filters.location)) return false;
      return true;
    });

    this.render();
  }

  resetFilters() {
    this.filters = { type: 'all', avail: 'available', maxPrice: 5000, search: '', location: '' };

    const sInput = document.getElementById('searchInput');
    const lInput = document.getElementById('locationFilter');
    const pRange = document.getElementById('priceRange');
    const pLabel = document.getElementById('priceLabel');

    if (sInput) sInput.value = '';
    if (lInput) lInput.value = '';
    if (pRange) pRange.value = 5000;
    if (pLabel) pLabel.textContent = '₹5,000';

    document.querySelectorAll('.sb-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.sb-group').forEach(group => {
      const firstTab = group.querySelector('.sb-tab');
      if (firstTab) firstTab.classList.add('active');
    });

    this.applyFilters();
  }

  render() {
    const grid = document.getElementById('vGrid');
    const count = document.getElementById('vCount');
    if (count) count.textContent = `${this.filteredVehicles.length} vehicle${this.filteredVehicles.length !== 1 ? 's' : ''} found`;

    if (!grid) return;

    if (this.filteredVehicles.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:80px 24px;">
          <i class="fas fa-search" style="font-size:48px;color:rgba(14,165,233,0.1);margin-bottom:20px;display:block;"></i>
          <h3 style="color:var(--text-secondary);">No matches found</h3>
          <p style="color:var(--text-muted);font-size:14px;">Try adjusting your filters or searching for something else.</p>
        </div>`;
      return;
    }

    grid.innerHTML = this.filteredVehicles.map(v => this.vehicleCard(v)).join('');
  }

  vehicleCard(v) {
    const avail = v.status === 'available';
    const typeIcon = v.type === 'bike' ? 'fa-motorcycle' : 'fa-car';
    const imgHtml = v.image
      ? `<img src="${v.image}&w=600&q=82&auto=format&fit=crop" alt="${v.name}" loading="lazy"
              onerror="this.style.display='none';this.parentElement.querySelector('.v-card-fallback').style.display='flex';">`
      : '';

    return `
      <div class="v-card ${avail ? '' : 'booked'}" onclick="window.location.href='/booking?vehicle_id=${v.id}'">
        <div class="v-card-img">
          <div class="v-card-fallback" style="display:${v.image ? 'none' : 'flex'};height:100%;align-items:center;justify-content:center;background:rgba(14,165,233,0.05);">
            <i class="fas ${typeIcon}" style="font-size:50px;color:rgba(14,165,233,0.15);"></i>
          </div>
          ${imgHtml}
          <div class="v-card-badges">
            <span class="badge ${v.type === 'bike' ? 'badge-bike' : 'badge-car'}">${v.type}</span>
            <span class="badge ${avail ? 'badge-available' : 'badge-booked'}">
              ${avail ? '● Available' : '● Booked'}
            </span>
          </div>
        </div>
        <div class="v-card-body">
          <div class="v-card-name">${v.name}</div>
          <div class="v-card-meta">
            <span><i class="fas fa-map-marker-alt"></i> ${v.location || 'City'}</span>
            <span><i class="fas fa-gas-pump"></i> ${v.fuel || 'Petrol'}</span>
            ${v.seats ? `<span><i class="fas fa-user"></i> ${v.seats} Seats</span>` : ''}
          </div>
          <div class="v-card-footer">
            <div class="v-card-price">
              <span class="amount">₹${(v.price_per_day || 0).toLocaleString('en-IN')}</span>
              <span class="period">/day</span>
            </div>
            ${avail
        ? `<a href="/booking?vehicle_id=${v.id}" class="btn-book-card" onclick="event.stopPropagation()">
                   <i class="fas fa-calendar-plus"></i> Book
                 </a>`
        : `<span class="btn-book-disabled"><i class="fas fa-lock"></i> Booked</span>`
      }
          </div>
        </div>
      </div>`;
  }

  setupSocket() {
    this.socket.on('vehicle_status_update', (data) => {
      console.log('Socket Event: vehicle_status_update', data);
      const vid = data.vehicle_id || data.id;
      const v = this.allVehicles.find(x => x.id === parseInt(vid));
      if (v) {
        v.status = data.status;
        this.applyFilters();
      }
    });

    this.socket.on('booking_status_update', (data) => {
      // If a booking is cancelled or completed, it might free up a vehicle
      if (data.status === 'Cancelled' || data.status === 'Completed') {
        this.loadVehicles(); // Reload to be safe as status logic can be complex
      }
    });

    this.socket.on('vehicle_added', () => this.loadVehicles());
    this.socket.on('booking_confirmed', () => this.loadVehicles());
    this.socket.on('booking_cancelled', () => this.loadVehicles());
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.vPage = new VehiclePage();
});
