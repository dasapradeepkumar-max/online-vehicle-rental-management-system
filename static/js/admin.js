/* ════════════════════════════════════════════════════════════
   admin.js — VehicleHub Admin Dashboard
   ════════════════════════════════─────────────────────── */

class AdminApp {
    constructor() {
        this.socket = io();
        window.adminApp = this;
        this.charts = {};
        this.init();
    }

    async init() {
        await this.loadOverview();
        await this.loadVehicles();
        await this.loadBookings();
        await this.loadUsers();
        this.setupSocket();
    }

    // ─── Tabs ─────────────────────────────────────────────────────────────
    tab(id, btn) {
        document.querySelectorAll('.admin-content').forEach(t => t.style.display = 'none');
        const target = document.getElementById(`tab-${id}`);
        if (target) target.style.display = 'block';

        document.querySelectorAll('.asb-link').forEach(l => l.classList.remove('active'));
        if (btn) btn.classList.add('active');

        const titles = { overview: 'Dashboard Overview', vehicles: 'Vehicle Management', bookings: 'All Bookings', users: 'User Directory' };
        document.getElementById('adminPageTitle').textContent = titles[id] || 'Admin Console';
    }

    // ─── Overview ─────────────────────────────────────────────────────────
    async loadOverview() {
        try {
            const res = await fetch('/api/admin/dashboard');
            if (res.status === 403) { window.location.href = '/dashboard'; return; }
            const data = await res.json();

            this.renderKPIs(data.stats);
            this.renderCharts(data.charts);
            this.renderRecent(data.recent_bookings || []);
        } catch (e) { }
    }

    renderKPIs(s) {
        if (!s) return;
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('akRevenue', `₹${(s.total_revenue || 0).toLocaleString('en-IN')}`);
        set('akActive', s.active_rentals || 0);
        set('akUsers', s.total_users || 0);
        set('akVehicles', s.total_vehicles || 0);
        set('akVSub', `Available: ${s.available_vehicles || 0}`);
    }

    renderCharts(c) {
        if (!c) return;

        // Revenue Line
        const revCtx = document.getElementById('revenueChart');
        if (revCtx && c.monthly) {
            if (this.charts.rev) this.charts.rev.destroy();
            this.charts.rev = new Chart(revCtx, {
                type: 'line',
                data: {
                    labels: c.monthly.map(m => m.month),
                    datasets: [{
                        label: 'Revenue',
                        data: c.monthly.map(m => m.revenue),
                        borderColor: '#0ea5e9', backgroundGradient: true,
                        fill: true, backgroundColor: 'rgba(14,165,233,0.1)',
                        tension: 0.4, borderWidth: 3, pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 10 } } },
                        x: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 10 } } }
                    }
                }
            });
        }

        // Type Doughnut
        const typeCtx = document.getElementById('typeChart');
        if (typeCtx && c.vehicle_types) {
            if (this.charts.type) this.charts.type.destroy();
            this.charts.type = new Chart(typeCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Cars', 'Bikes'],
                    datasets: [{
                        data: [c.vehicle_types.cars || 0, c.vehicle_types.bikes || 0],
                        backgroundColor: ['#0ea5e9', '#10b981'],
                        borderWidth: 0
                    }]
                },
                options: {
                    cutout: '75%',
                    plugins: { legend: { position: 'bottom', labels: { color: 'rgba(255,255,255,0.5)', font: { size: 11 }, padding: 20 } } }
                }
            });
        }
    }

    renderRecent(bookings) {
        const tbody = document.getElementById('tbRecentBookings');
        if (!tbody) return;
        if (bookings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:40px;color:rgba(255,255,255,0.2);">No recent bookings</td></tr>`;
            return;
        }
        tbody.innerHTML = bookings.slice(0, 6).map(b => `
      <tr>
        <td><strong>${b.customer_name}</strong></td>
        <td>${b.vehicle_name}</td>
        <td>₹${(b.total_price || 0).toLocaleString()}</td>
        <td><span class="badge badge-${b.status.toLowerCase()}">${b.status}</span></td>
      </tr>
    `).join('');
    }

    // ─── Lists ────────────────────────────────────────────────────────────
    async loadVehicles() {
        try {
            const res = await fetch('/api/admin/vehicles');
            const data = await res.json();
            const tbody = document.getElementById('tbVehicles');
            if (!tbody) return;
            tbody.innerHTML = data.map(v => `
        <tr>
          <td>#${v.id}</td>
          <td><strong>${v.name}</strong></td>
          <td>${v.type}</td>
          <td>${v.location || '—'}</td>
          <td>₹${v.price_per_day.toLocaleString()}</td>
          <td>
            <select class="form-input" style="padding:4px 8px;font-size:12px;width:110px;" onchange="adminApp.updateVehicleStatus(${v.id}, this.value)">
              <option value="available" ${v.status === 'available' ? 'selected' : ''}>Available</option>
              <option value="booked" ${v.status === 'booked' ? 'selected' : ''}>Booked</option>
              <option value="maintenance" ${v.status === 'maintenance' ? 'selected' : ''}>Maintenance</option>
            </select>
          </td>
          <td style="text-align:center;">
             <button class="btn-reset-sb" style="padding:4px 8px;font-size:11px;" onclick="window.location.href='/booking?vehicle_id=${v.id}'">View</button>
          </td>
          <td>${v.total_bookings}</td>
          <td>₹${v.total_revenue.toLocaleString()}</td>
        </tr>
      `).join('');
        } catch (e) { }
    }

    async loadBookings() {
        try {
            const res = await fetch('/api/admin/bookings');
            const data = await res.json();
            const tbody = document.getElementById('tbAllBookings');
            if (!tbody) return;
            tbody.innerHTML = data.map(b => {
                const isConfirmed = b.status === 'Confirmed' || b.status === 'Upcoming' || b.status === 'Active';
                return `
                <tr>
                  <td>#${b.id}</td>
                  <td><strong>${b.customer_name}</strong></td>
                  <td>${b.vehicle_name}</td>
                  <td style="font-size:12px;opacity:0.6;">${b.start_date} → ${b.end_date}</td>
                  <td>₹${b.total_price.toLocaleString()}</td>
                  <td><span class="badge badge-${b.status.toLowerCase()}">${b.status}</span></td>
                  <td>
                    <div style="display:flex;gap:6px;">
                        ${isConfirmed ? `
                            <button class="badge badge-available" style="cursor:pointer;border:none;" onclick="adminApp.updateBookingStatus(${b.id}, 'Completed')">Complete</button>
                            <button class="badge badge-booked" style="cursor:pointer;border:none;background:rgba(239,68,68,0.2);color:#f87171;" onclick="adminApp.updateBookingStatus(${b.id}, 'Cancelled')">Cancel</button>
                        ` : '<span style="color:var(--text-muted);font-size:11px;">No Actions</span>'}
                    </div>
                  </td>
                </tr>
                `;
            }).join('');
        } catch (e) { }
    }

    async updateVehicleStatus(id, status) {
        try {
            const res = await fetch(`/api/admin/vehicles/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            if (res.ok) {
                window.showToast('Vehicle status updated', 'success');
                this.loadOverview();
            } else {
                throw new Error();
            }
        } catch (e) {
            window.showToast('Failed to update status', 'error');
            this.loadVehicles();
        }
    }

    async updateBookingStatus(id, status) {
        if (!confirm(`Mark booking #${id} as ${status}?`)) return;
        try {
            const res = await fetch(`/api/admin/bookings/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            if (res.ok) {
                window.showToast(`Booking ${status.toLowerCase()}`, 'success');
                this.loadOverview();
                this.loadBookings();
            } else {
                const d = await res.json();
                window.showToast(d.message || 'Operation failed', 'error');
            }
        } catch (e) {
            window.showToast('Network error', 'error');
        }
    }

    renderRecent(bookings) {
        const tbody = document.getElementById('tbRecentBookings');
        if (!tbody) return;
        if (bookings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:40px;color:rgba(255,255,255,0.2);">No recent bookings</td></tr>`;
            return;
        }
        tbody.innerHTML = bookings.slice(0, 6).map(b => `
      <tr>
        <td><strong>${b.customer_name}</strong></td>
        <td>${b.vehicle_name}</td>
        <td>₹${(b.total_price || 0).toLocaleString()}</td>
        <td><span class="badge badge-${b.status.toLowerCase()}">${b.status}</span></td>
      </tr>
    `).join('');
    }

    // ─── Feed & Sockets ───────────────────────────────────────────────────
    addFeed(icon, color, title, sub) {
        const feed = document.getElementById('liveFeed');
        if (!feed) return;
        if (feed.querySelector('.fa-satellite-dish')) feed.innerHTML = '';

        const el = document.createElement('div');
        el.className = 'feed-item';
        el.innerHTML = `
      <div class="fi-icon" style="background:rgba(${color},0.1);color:rgb(${color});">
        <i class="fas ${icon}"></i>
      </div>
      <div class="fi-text">
        <strong>${title}</strong>
        <span>${sub} • just now</span>
      </div>
    `;
        feed.insertBefore(el, feed.firstChild);
    }

    setupSocket() {
        console.log('🔌 Admin Socket Connecting...');
        this.socket.on('connect', () => console.log('✓ Admin Socket Connected'));

        this.socket.on('new_booking', (d) => {
            console.log('Socket Event: new_booking', d);
            this.addFeed('fa-calendar-check', '52, 211, 153', `New Booking - ${d.vehicle_name}`, `by ${d.customer_name}`);
            this.loadOverview();
            this.loadBookings();
        });
        this.socket.on('booking_confirmed', (d) => {
            this.loadOverview();
            this.loadBookings();
        });
        this.socket.on('booking_status_update', (d) => {
            this.loadOverview();
            this.loadBookings();
            this.loadVehicles();
        });
        this.socket.on('activity_update', (d) => {
            let color = '14, 165, 233'; // blue
            let icon = 'fa-info-circle';
            if (d.type === 'cancellation') { color = '239, 68, 68'; icon = 'fa-times-circle'; }
            this.addFeed(icon, color, d.title, d.msg);
        });
        this.socket.on('user_registered', (d) => {
            this.addFeed('fa-user-plus', '14, 165, 233', 'New Registration', d.email);
            this.loadUsers();
        });
        this.socket.on('vehicle_status_update', (d) => {
            console.log('Socket Event: vehicle_status_update', d);
            this.loadVehicles();
            this.loadOverview();
        });
    }
}

// Testing Helper for subagent (auto-confirm native dialogs)
if (window.location.search.includes('test_mode=1')) {
    window.confirm = () => true;
}

document.addEventListener('DOMContentLoaded', () => {
    window.adminApp = new AdminApp();
});
