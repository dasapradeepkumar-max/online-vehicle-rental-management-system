/* ════════════════════════════════════════════════════════════
   mybookings.js — VehicleHub User Bookings
   ════════════════════════════════════════════════════════════ */

class BookingsApp {
    constructor() {
        this.all = [];
        this.currentFilter = 'all';
        this.socket = io();
        this.init();
    }

    async init() {
        await this.load();
        this.setupSocket();
    }

    async load() {
        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch('/api/bookings/my', {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (res.status === 401) { window.location.href = '/login'; return; }
            if (!res.ok) throw new Error();
            this.all = await res.json();
            this.render();
        } catch (e) {
            document.getElementById('bookingsContainer').innerHTML = `
        <div class="empty-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>Failed to load bookings</h3>
          <p>Please refresh the page</p>
        </div>`;
        }
    }

    filter(status, btn) {
        this.currentFilter = status;
        document.querySelectorAll('.mf-tab').forEach(t => t.classList.remove('active'));
        if (btn) btn.classList.add('active');
        this.render();
    }

    render() {
        this.renderStats();

        const list = this.currentFilter === 'all'
            ? this.all
            : this.all.filter(b => b.status === this.currentFilter);

        const container = document.getElementById('bookingsContainer');
        if (!container) return;

        if (list.length === 0) {
            container.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-calendar-times"></i>
          <h3>No bookings found</h3>
          <p>${this.currentFilter === 'all' ? "You haven't made any bookings yet." : `No ${this.currentFilter.toLowerCase()} bookings found.`}</p>
          <a href="/vehicles" class="btn-primary" style="margin-top:20px;">
            <i class="fas fa-car"></i> Browse Vehicles
          </a>
        </div>`;
            return;
        }

        container.innerHTML = list.map(b => this.bookingCard(b)).join('');
    }

    renderStats() {
        const active = this.all.filter(b => b.status === 'Active').length;
        const upcoming = this.all.filter(b => b.status === 'Upcoming').length;
        const spent = this.all.filter(b => b.status !== 'Cancelled').reduce((s, b) => s + (b.total_price || 0), 0);

        document.getElementById('mbTotal').textContent = this.all.length;
        document.getElementById('mbActive').textContent = active;
        document.getElementById('mbUpcoming').textContent = upcoming;
        document.getElementById('mbSpent').textContent = `₹${spent.toLocaleString('en-IN')}`;
    }

    bookingCard(b) {
        const typeIcon = b.vehicle_type === 'bike' ? 'fa-motorcycle' : 'fa-car';
        const statusClass = `badge-${b.status.toLowerCase()}`;
        const canCancel = b.status === 'Upcoming' || b.status === 'Confirmed';

        const start = new Date(b.start_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
        const end = new Date(b.end_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

        const imgHtml = b.vehicle_image
            ? `<img src="${b.vehicle_image}" class="bc-img" alt="${b.vehicle_name}" onerror="this.style.display='none';this.parentElement.querySelector('.bc-icon').style.display='flex';">`
            : '';

        return `
      <div class="booking-card" id="bk-${b.id}">
        <div style="position:relative;">
          <div class="bc-icon" style="display:${b.vehicle_image ? 'none' : 'flex'};">
            <i class="fas ${typeIcon}"></i>
          </div>
          ${imgHtml}
        </div>
        <div class="bc-info">
          <div class="bc-name">${b.vehicle_name}</div>
          <div class="bc-dates">
            <i class="fas fa-calendar-alt"></i> ${start} — ${end}
            <span style="opacity:0.3;margin:0 4px;">•</span>
            <i class="fas fa-moon"></i> ${b.days} night${b.days > 1 ? 's' : ''}
          </div>
          <div class="bc-tags">
            <span class="badge ${statusClass}">${b.status}</span>
            <span class="badge badge-car" style="opacity:0.6;">${b.vehicle_type}</span>
            <span style="font-size:11px;color:var(--text-muted);margin-left:4px;">#BK-${b.id}</span>
          </div>
        </div>
        <div class="bc-right">
          <div class="bc-price">₹${(b.total_price || 0).toLocaleString('en-IN')}</div>
          <div class="bc-nights">₹${(b.price_per_day || 0).toLocaleString('en-IN')}/day</div>
          ${canCancel
                ? `<button class="btn-cancel-bk" onclick="bookingsApp.cancel(${b.id}, this)">
                 <i class="fas fa-times"></i> Cancel
               </button>`
                : ''
            }
        </div>
      </div>`;
    }

    async cancel(id, btn) {
        if (!confirm('Are you sure you want to cancel this booking?')) return;

        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cancelling...';

        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch(`/api/bookings/${id}/cancel`, {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (res.ok) {
                const data = await res.json();
                if (data.fee !== undefined && data.fee > 0) {
                    window.showToast(`Booking cancelled. Fee: ₹${data.fee.toFixed(2)}, Refund: ₹${data.refund.toFixed(2)}`, 'success');
                } else {
                    window.showToast('Booking cancelled successfully. Full refund initiated.', 'success');
                }
                await this.load();
            } else {
                const d = await res.json();
                window.showToast(d.message || 'Cancellation failed', 'error');
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        } catch (e) {
            window.showToast('Network error', 'error');
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    setupSocket() {
        this.socket.on('booking_confirmed', () => this.load());
        this.socket.on('booking_cancelled', () => this.load());
        this.socket.on('vehicle_status_update', () => this.load());
    }
}

// Testing Helper for subagent (auto-confirm native dialogs)
if (window.location.search.includes('test_mode=1')) {
    window.confirm = () => true;
}

document.addEventListener('DOMContentLoaded', () => {
    window.bookingsApp = new BookingsApp();
});
