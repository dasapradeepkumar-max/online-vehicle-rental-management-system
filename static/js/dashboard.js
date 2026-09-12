/* ════════════════════════════════════════════════════════════
   dashboard.js — VehicleHub User Dashboard
   ════════════════════════════════════════════════════════════ */

class DashboardApp {
    constructor() {
        this.user = null;
        this.socket = io();
        this.init();
    }

    isVisibleBooking(booking) {
        return !['Completed', 'Cancelled'].includes(booking.status);
    }

    async init() {
        await this.loadUser();
        await this.loadStats();
        await this.loadRecent();
        this.setupSocket();
    }

    async loadUser() {
        const token = localStorage.getItem('auth_token');
        if (!token) { window.location.href = '/login'; return; }

        try {
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                this.user = await res.json();
                const welcome = document.getElementById('welcomeText');
                if (welcome) welcome.textContent = `Welcome back, ${this.user.full_name.split(' ')[0]} 👋`;
            }
        } catch (e) { }
    }

    async loadStats() {
        try {
            const res = await fetch('/api/public/stats');
            const d = await res.json();

            const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

            set('lTotalV', d.total_vehicles);
            set('lAvailV', d.available_vehicles);
            set('lActiveR', d.active_bookings);
            set('lUsers', d.total_users);

            set('dAvailVehicles', d.available_vehicles);
        } catch (e) { }

        // Load user specifically stats
        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch('/api/bookings/my', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const bookings = await res.json();
                const visibleBookings = bookings.filter(b => this.isVisibleBooking(b));
                const active = visibleBookings.filter(b => b.status === 'Active').length;
                const upcoming = visibleBookings.filter(b => b.status === 'Upcoming').length;
                const spent = bookings.filter(b => b.status !== 'Cancelled').reduce((s, b) => s + (b.total_price || 0), 0);

                document.getElementById('dActiveRentals').textContent = active;
                document.getElementById('dUpcoming').textContent = upcoming;
                document.getElementById('dSpent').textContent = `₹${spent.toLocaleString('en-IN')}`;
            }
        } catch (e) { }
    }

    async loadRecent() {
        const list = document.getElementById('recentBookingsList');
        if (!list) return;

        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch('/api/bookings/my', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const bookings = await res.json();
            const recent = bookings.filter(b => this.isVisibleBooking(b)).slice(0, 4);

            if (recent.length === 0) {
                list.innerHTML = `<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px;">No recent bookings found.</div>`;
                return;
            }

            list.innerHTML = recent.map(b => `
        <div class="bk-row">
          <div class="bk-dot" style="background:${this.statusColor(b.status)};"></div>
          <div class="bk-info">
            <div class="bk-name">${b.vehicle_name}</div>
            <div class="bk-date">${new Date(b.start_date).toLocaleDateString()} — ${b.status}</div>
          </div>
          <div class="bk-amount">₹${(b.total_price || 0).toLocaleString('en-IN')}</div>
        </div>
      `).join('');
        } catch (e) {
            list.innerHTML = `<div style="color:#f87171;font-size:12px;">Error loading bookings.</div>`;
        }
    }

    statusColor(s) {
        if (s === 'Active') return '#10b981';
        if (s === 'Upcoming') return '#fbbf24';
        if (s === 'Cancelled') return '#f87171';
        return '#6366f1';
    }

    setupSocket() {
        this.socket.on('stats_update', () => this.loadStats());
        this.socket.on('booking_confirmed', () => {
            this.loadStats();
            this.loadRecent();
        });
        this.socket.on('booking_cancelled', () => {
            this.loadStats();
            this.loadRecent();
        });
        this.socket.on('booking_status_update', () => {
            this.loadStats();
            this.loadRecent();
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.dashApp = new DashboardApp();
});
