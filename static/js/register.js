class RegisterApp {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 3;
        this.userData = {};
        this.otp_session_id = null;
        this.otpTimer = null;
        this.resendTimer = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupOTPInputHandlers();
    }

    setupEventListeners() {
        // Password strength indicator
        const passwordInput = document.getElementById('password');
        if (passwordInput) {
            passwordInput.addEventListener('input', (e) => {
                this.checkPasswordStrength(e.target.value);
            });
        }
    }

    setupOTPInputHandlers() {
        const otpInputs = document.querySelectorAll('.otp-input');
        otpInputs.forEach((input, index) => {
            input.addEventListener('keyup', (e) => {
                if (e.key === 'Backspace') {
                    input.value = '';
                    if (index > 0) {
                        otpInputs[index - 1].focus();
                    }
                } else if (/[0-9]/.test(e.key)) {
                    input.value = e.key;
                    if (index < otpInputs.length - 1) {
                        otpInputs[index + 1].focus();
                    } else {
                        // All OTP boxes filled - auto submit
                        this.verifyAndRegister();
                    }
                }
            });

            // Handle paste
            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const pastedData = (e.clipboardData || window.clipboardData).getData('text');
                const digits = pastedData.replace(/\D/g, '').split('');
                digits.forEach((digit, i) => {
                    if (index + i < otpInputs.length) {
                        otpInputs[index + i].value = digit;
                    }
                });
                if (digits.length > 0) {
                    otpInputs[Math.min(index + digits.length - 1, otpInputs.length - 1)].focus();
                }
            });
        });
    }

    checkPasswordStrength(password) {
        const strength = document.getElementById('passwordStrength');
        let score = 0;

        if (password.length >= 8) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[^a-zA-Z0-9]/.test(password)) score++;

        strength.classList.remove('weak', 'medium', 'strong');
        if (score === 1 || score === 2) {
            strength.classList.add('weak');
        } else if (score === 3 || score === 4) {
            strength.classList.add('medium');
        } else if (score === 5) {
            strength.classList.add('strong');
        }
    }

    validateStep1() {
        const fullName = document.getElementById('fullName').value.trim();
        const email = document.getElementById('email').value.trim();
        const phone = document.getElementById('phone').value.trim();

        // Validate name
        if (!fullName) {
            this.showError('nameError', 'Full name is required');
            return false;
        }

        // Validate email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            this.showError('emailError', 'Please enter a valid email');
            return false;
        }

        // Validate phone (if provided)
        if (phone && !/^\d{10}$/.test(phone.replace(/\D/g, ''))) {
            this.showError('phoneError', 'Phone must be 10 digits');
            return false;
        }

        this.userData.full_name = fullName;
        this.userData.email = email;
        this.userData.phone = phone || null;

        return true;
    }

    validateStep2() {
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        if (password.length < 8) {
            alert('Password must be at least 8 characters');
            return false;
        }

        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return false;
        }

        // Check password strength
        let score = 0;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/[0-9]/.test(password)) score++;
        if (/[^a-zA-Z0-9]/.test(password)) score++;

        if (score < 3) {
            alert('Password must contain uppercase, lowercase, number, and special character');
            return false;
        }

        this.userData.password = password;
        return true;
    }

    nextStep() {
        if (this.currentStep === 1) {
            if (!this.validateStep1()) return;
            this.goToStep(2);
        } else if (this.currentStep === 2) {
            if (!this.validateStep2()) return;
            this.sendOTP();
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.goToStep(this.currentStep - 1);
        }
    }

    goToStep(step) {
        // Hide current step
        document.getElementById(`step-${this.currentStep}`).classList.remove('active');
        document.getElementById(`step${this.currentStep}-ind`).classList.remove('active');

        // Show new step
        this.currentStep = step;
        document.getElementById(`step-${step}`).classList.add('active');
        document.getElementById(`step${step}-ind`).classList.add('active');

        // Mark previous steps as completed
        for (let i = 1; i < step; i++) {
            document.getElementById(`step${i}-ind`).classList.add('completed');
        }
    }

    async sendOTP() {
        try {
            const response = await fetch('/api/auth/send-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    identifier: this.userData.email,
                    action: 'register'
                })
            });

            const data = await response.json();

            if (!response.ok) {
                alert('Error: ' + (data.message || 'Failed to send OTP'));
                return;
            }

            this.otp_session_id = data.session_id;
            document.getElementById('otpEmail').textContent = data.identifier;
            this.goToStep(3);
            this.startOTPTimer();
            this.startResendTimer();

        } catch (error) {
            console.error('Error:', error);
            alert('Failed to send OTP');
        }
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
                this.previousStep();
            }
        };

        updateTimer();
    }

    startResendTimer() {
        let timeLeft = 30;
        const resendBtn = document.getElementById('resendBtn');
        resendBtn.style.display = 'none';

        const updateResendTimer = () => {
            if (timeLeft > 0) {
                timeLeft--;
                resendBtn.textContent = `Resend OTP in ${timeLeft}s`;
                this.resendTimer = setTimeout(updateResendTimer, 1000);
            } else {
                resendBtn.style.display = 'block';
                resendBtn.textContent = 'Resend OTP';
            }
        };

        updateResendTimer();
    }

    async resendOTP() {
        clearTimeout(this.otpTimer);
        clearTimeout(this.resendTimer);

        // Clear OTP boxes
        document.querySelectorAll('.otp-input').forEach(input => {
            input.value = '';
            input.classList.remove('is-invalid');
        });

        await this.sendOTP();
    }

    async verifyAndRegister() {
        const otpInputs = document.querySelectorAll('.otp-input');
        const otp = Array.from(otpInputs).map(input => input.value).join('');

        if (otp.length !== 6) {
            alert('Please enter complete 6-digit OTP');
            return;
        }

        try {
            // Verify OTP
            const verifyResponse = await fetch('/api/auth/verify-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    identifier: this.userData.email,
                    otp: otp,
                    session_id: this.otp_session_id
                })
            });

            const verifyData = await verifyResponse.json();

            if (!verifyResponse.ok) {
                alert('Invalid OTP: ' + (verifyData.message || 'Verification failed'));
                this.shakeOTPBoxes();
                return;
            }

            // Now register the user
            const registerResponse = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${verifyData.token}`
                },
                body: JSON.stringify(this.userData)
            });

            const registerData = await registerResponse.json();

            if (!registerResponse.ok) {
                alert('Registration failed: ' + (registerData.message || 'An error occurred'));
                return;
            }

            // Store token
            localStorage.setItem('auth_token', verifyData.token);
            localStorage.setItem('user_data', JSON.stringify(registerData.user));

            // Show success message
            alert('Account created successfully!');

            // Redirect to dashboard
            window.location.href = '/dashboard';

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        }
    }

    shakeOTPBoxes() {
        const container = document.getElementById('otpContainer');
        container.classList.add('shake');
        setTimeout(() => {
            container.classList.remove('shake');
        }, 500);
    }

    showError(elementId, message) {
        const errorElement = document.getElementById(elementId);
        if (errorElement) {
            errorElement.textContent = message;
        }
    }

    togglePassword() {
        const passwordInput = document.getElementById('password');
        const toggleBtn = document.querySelector('.toggle-password');

        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
        } else {
            passwordInput.type = 'password';
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.registerApp = new RegisterApp();
});
