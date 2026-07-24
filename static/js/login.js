class LoginApp {
    constructor() {
        this.currentStep = 1;
        this.identifier = null;
        this.otpTimer = null;
        this.resendTimer = null;
        this.init();
    }

    init() {
        this.setupEnterKey();
        this.setupOTPHandlers();
    }

    setupEnterKey() {
        document.getElementById('identifier').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendOTP();
            }
        });
    }

    setupOTPHandlers() {
        const inputs = document.querySelectorAll('.otp-input');
        inputs.forEach((input, index) => {
            input.addEventListener('keyup', (e) => {
                if (e.key === 'Backspace') {
                    input.value = '';
                    if (index > 0) {
                        inputs[index - 1].focus();
                    }
                } else if (/[0-9]/.test(e.key)) {
                    input.value = e.key;
                    if (index < inputs.length - 1) {
                        inputs[index + 1].focus();
                    } else {
                        // Last digit entered, auto-submit
                        setTimeout(() => this.verifyOTP(), 300);
                    }
                }
            });

            // Handle paste
            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const pastedData = (e.clipboardData || window.clipboardData).getData('text');
                const digits = pastedData.replace(/\D/g, '').split('');
                digits.forEach((digit, i) => {
                    if (index + i < inputs.length) {
                        inputs[index + i].value = digit;
                    }
                });
            });
        });
    }

    async sendOTP() {
        const identifier = document.getElementById('identifier').value.trim();

        // Validate
        if (!identifier) {
            alert('Please enter email or phone number');
            return;
        }

        // Check format
        const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier);
        const isPhone = /^\d{10}$/.test(identifier.replace(/\D/g, ''));

        if (!isEmail && !isPhone) {
            alert('Please enter a valid email or 10-digit phone number');
            return;
        }

        try {
            const response = await fetch('/api/auth/send-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    identifier: identifier,
                    action: 'login'
                })
            });

            const data = await response.json();

            if (!response.ok) {
                alert('Error: ' + (data.message || 'Failed to send OTP'));
                return;
            }

            // Store identifier and move to step 2
            this.identifier = identifier;
            document.getElementById('displayEmail').textContent = this.maskIdentifier(identifier);
            this.showStep(2);
            this.startOTPTimer();
            this.startResendTimer();

        } catch (error) {
            console.error('Error:', error);
            alert('Failed to send OTP. Please try again');
        }
    }

    async verifyOTP() {
        const inputs = document.querySelectorAll('.otp-input');
        const otp = Array.from(inputs).map(input => input.value).join('');

        if (otp.length !== 6) {
            alert('Please enter the complete 6-digit code');
            return;
        }

        try {
            const response = await fetch('/api/auth/verify-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    identifier: this.identifier,
                    otp: otp
                })
            });

            const data = await response.json();

            if (!response.ok) {
                alert('Invalid OTP: ' + (data.message || 'Verification failed'));
                this.shakeOTPBoxes();
                return;
            }

            // Store token and user data
            localStorage.setItem('auth_token', data.token);
            localStorage.setItem('user_data', JSON.stringify(data.user));

            // Redirect to dashboard
            window.location.href = data.redirect_url || '/dashboard';

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred. Please try again');
        }
    }

    resendOTP() {
        clearTimeout(this.otpTimer);
        clearTimeout(this.resendTimer);

        // Clear OTP boxes
        document.querySelectorAll('.otp-input').forEach(input => {
            input.value = '';
            input.classList.remove('error');
        });

        this.sendOTP();
    }

    backToEmail() {
        clearTimeout(this.otpTimer);
        clearTimeout(this.resendTimer);
        this.showStep(1);
    }

    showStep(step) {
        // Hide all sections
        document.querySelectorAll('.form-section').forEach(section => {
            section.classList.add('hidden');
        });

        // Show selected section
        document.getElementById(`step-${step}`).classList.remove('hidden');
        this.currentStep = step;
    }

    startOTPTimer() {
        let timeLeft = 300; // 5 minutes
        const timerElement = document.getElementById('otpTimer');

        const updateTimer = () => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            if (timeLeft > 0) {
                timeLeft--;
                this.otpTimer = setTimeout(updateTimer, 1000);
            } else {
                alert('OTP expired. Please request a new one.');
                this.backToEmail();
            }
        };

        updateTimer();
    }

    startResendTimer() {
        let timeLeft = 30;
        const resendBtn = document.getElementById('resendBtn');
        resendBtn.style.display = 'none';

        const updateTimer = () => {
            if (timeLeft > 0) {
                timeLeft--;
                this.resendTimer = setTimeout(updateTimer, 1000);
            } else {
                resendBtn.style.display = 'block';
            }
        };

        updateTimer();
    }

    shakeOTPBoxes() {
        document.querySelectorAll('.otp-input').forEach(input => {
            input.classList.add('error');
            setTimeout(() => input.classList.remove('error'), 500);
        });
    }

    maskIdentifier(identifier) {
        if (identifier.includes('@')) {
            const [local, domain] = identifier.split('@');
            const masked = local.substring(0, 2) + '*'.repeat(Math.max(0, local.length - 2)) + '@' + domain;
            return masked;
        } else {
            return identifier.substring(0, 3) + '*'.repeat(7);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.loginApp = new LoginApp();
});

// Auto-logout if token expires
setInterval(() => {
    const token = localStorage.getItem('auth_token');
    if (!token && window.location.pathname === '/dashboard') {
        window.location.href = '/login';
    }
}, 60000);
