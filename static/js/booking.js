/* ════════════════════════════════════════════════════════════
   booking.js — VehicleHub Real-Time Booking
   ════════════════════════════════════════════════════════════ */

class BookingApp {
    constructor() {
        this.vehicleId = null;
        this.vehicle = null;
        this.socket = io();
        this.init();
    }

    async init() {
        const params = new URLSearchParams(window.location.search);
        this.vehicleId = params.get('vehicle_id');

        if (!this.vehicleId) {
            window.showToast('No vehicle selected', 'error');
            setTimeout(() => window.location.href = '/vehicles', 2000);
            return;
        }

        await this.loadVehicle();
        this.setupDateLogic();
        this.setupForm();
        this.setupSocket();
    }

    async loadVehicle() {
        try {
            const res = await fetch(`/api/vehicles/${this.vehicleId}`);
            if (!res.ok) throw new Error('Vehicle not found');
            this.vehicle = await res.json();
            this.renderPreview();
        } catch (e) {
            window.showToast('Failed to load vehicle details', 'error');
        }
    }

    renderPreview() {
        const v = this.vehicle;
        if (!v) return;

        document.getElementById('vName').textContent = v.name;
        document.getElementById('vPriceDisplay').innerHTML = `₹${(v.price_per_day || 0).toLocaleString('en-IN')}<span>/day</span>`;
        document.getElementById('bdRate').textContent = `₹${(v.price_per_day || 0).toLocaleString('en-IN')}`;

        // Hidden input
        const vIdInput = document.getElementById('vehicleIdInput');
        if (vIdInput) vIdInput.value = v.id;

        // Meta details
        const metaEl = document.getElementById('vMeta');
        const icon = v.type === 'bike' ? 'fa-motorcycle' : 'fa-car';
        metaEl.innerHTML = `
      <span><i class="fas ${icon}"></i> ${v.type.toUpperCase()}</span>
      <span><i class="fas fa-map-marker-alt"></i> ${v.location || 'City'}</span>
      <span><i class="fas fa-gas-pump"></i> ${v.fuel || 'Petrol'}</span>
    `;

        // Image logic
        const imgWrap = document.getElementById('vehiclePreview');
        const fallback = document.getElementById('imgFallback');
        if (v.image) {
            if (fallback) fallback.style.display = 'none';
            const img = document.createElement('img');
            img.src = `${v.image}&w=800&q=82&auto=format&fit=crop`;
            img.alt = v.name;
            img.style.cssText = 'width:100%;height:220px;object-fit:cover;display:block;';
            imgWrap.prepend(img);
        } else if (fallback) {
            fallback.style.display = 'flex';
            fallback.querySelector('i').className = `fas ${icon}`;
        }

        // Initial check
        if (v.status !== 'available') {
            this.showAvailability('busy', 'This vehicle is currently booked for today');
            document.getElementById('confirmBtn').disabled = true;
        }
    }

    setupDateLogic() {
        const startEl = document.getElementById('startDate');
        const endEl = document.getElementById('endDate');
        if (!startEl || !endEl) return;

        const today = new Date().toISOString().split('T')[0];
        const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];

        startEl.min = today;
        startEl.value = today;
        endEl.min = tomorrow;
        endEl.value = tomorrow;

        const changeHandler = () => {
            const start = new Date(startEl.value);
            const minEnd = new Date(start.getTime() + 86400000).toISOString().split('T')[0];
            endEl.min = minEnd;
            if (endEl.value <= startEl.value) endEl.value = minEnd;
            this.updateTotal();
            this.checkAvailability();
        };

        startEl.addEventListener('change', changeHandler);
        endEl.addEventListener('change', changeHandler);
        this.updateTotal();
    }

    updateTotal() {
        if (!this.vehicle) return;
        const start = new Date(document.getElementById('startDate').value);
        const end = new Date(document.getElementById('endDate').value);
        const diff = end - start;
        const days = Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)));

        document.getElementById('bdDays').textContent = `${days} day${days > 1 ? 's' : ''}`;
        const total = days * this.vehicle.price_per_day;
        document.getElementById('bdTotal').textContent = `₹${total.toLocaleString('en-IN')}`;
    }

    async checkAvailability() {
        const start = document.getElementById('startDate').value;
        const end = document.getElementById('endDate').value;
        if (!start || !end) return;

        this.showAvailability('check', 'Checking availability...');
        const btn = document.getElementById('confirmBtn');
        btn.disabled = true;

        try {
            const res = await fetch(`/api/public/availability/${this.vehicleId}?start_date=${start}&end_date=${end}`);
            const data = await res.json();
            if (data.available) {
                this.showAvailability('ok', '✓ Vehicle is available for these dates');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Confirm Booking';
            } else {
                this.showAvailability('busy', '✗ Not available for selected dates');
                btn.disabled = true;
                btn.innerHTML = '<i class="fas fa-lock"></i> Dates Unavailable';
            }
        } catch (e) {
            this.showAvailability('busy', 'Error checking availability');
        }
    }

    showAvailability(type, msg) {
        const el = document.getElementById('availIndicator');
        if (!el) return;
        el.style.display = 'flex';
        el.className = `avail-ind avail-${type}`;
        const icon = type === 'ok' ? 'fa-check-circle' : (type === 'busy' ? 'fa-times-circle' : 'fa-spinner fa-spin');
        el.innerHTML = `<i class="fas ${icon}"></i> ${msg}`;
    }

    setupForm() {
        const form = document.getElementById('bookingForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitBooking();
            });
        }
    }

    async submitBooking() {
        const btn = document.getElementById('confirmBtn');
        const start = document.getElementById('startDate').value;
        const end = document.getElementById('endDate').value;
        const pickupTime = document.getElementById('pickupTime').value;
        const returnTime = document.getElementById('returnTime').value;

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

        const token = localStorage.getItem('auth_token');

        try {
            const res = await fetch('/api/bookings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                    vehicle_id: parseInt(this.vehicleId),
                    start_date: start,
                    end_date: end,
                    pickup_time: pickupTime,
                    return_time: returnTime
                })
            });

            const data = await res.json();
            if (res.ok) {
                window.showToast('Booking success! Redirecting...', 'success');
                setTimeout(() => window.location.href = '/mybookings', 1500);
            } else {
                window.showToast(data.message || 'Booking failed', 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Try Again';
            }
        } catch (e) {
            window.showToast('Network error', 'error');
            btn.disabled = false;
        }
    }

    setupSocket() {
        this.socket.on('vehicle_status_update', (data) => {
            if (data.vehicle_id == this.vehicleId) {
                this.checkAvailability();
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.bookingApp = new BookingApp();
});
