// AUTH.JS - PROFESSIONAL OTP LOGIN FLOW

class OTPAuth {
  constructor() {
    this.currentStep = 1;
    this.identifier = '';
    this.otp = '';
    this.timerInterval = null;
    this.resendInterval = null;
    this.otpExpiring = false;
    this.otpAttempts = 0;
    this.maxAttempts = 5;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupOTPInputHandlers();
  }

  setupEventListeners() {
    // Email/Phone Form
    const emailForm = document.getElementById('emailForm');
    if (emailForm) {
      emailForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleSendOTP();
      });
    }

    // OTP Form
    const otpForm = document.getElementById('otpForm');
    if (otpForm) {
      otpForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleVerifyOTP();
      });
    }

    // Resend OTP
    const resendBtn = document.getElementById('resendBtn');
    if (resendBtn) {
      resendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.handleResendOTP();
      });
    }

    // Input validation
    const identifierInput = document.getElementById('identifier');
    if (identifierInput) {
      identifierInput.addEventListener('input', (e) => {
        this.validateIdentifier(e.target.value);
      });
    }
  }

  setupOTPInputHandlers() {
    const otpBoxes = document.querySelectorAll('.otp-box');

    otpBoxes.forEach((box, index) => {
      box.addEventListener('input', (e) => {
        // Only allow digits
        e.target.value = e.target.value.replace(/[^0-9]/g, '');

        if (e.target.value.length === 1) {
          box.classList.add('filled');
          // Auto-focus next input
          if (index < otpBoxes.length - 1) {
            otpBoxes[index + 1].focus();
          }
        } else {
          box.classList.remove('filled');
        }

        // Auto-submit if all filled
        const allFilled = Array.from(otpBoxes).every(b => b.value.length === 1);
        if (allFilled) {
          this.handleVerifyOTP();
        }
      });

      box.addEventListener('keydown', (e) => {
        // Handle backspace
        if (e.key === 'Backspace') {
          box.value = '';
          box.classList.remove('filled');
          if (index > 0) {
            otpBoxes[index - 1].focus();
          }
        }
        // Handle arrow keys
        if (e.key === 'ArrowLeft' && index > 0) {
          otpBoxes[index - 1].focus();
        }
        if (e.key === 'ArrowRight' && index < otpBoxes.length - 1) {
          otpBoxes[index + 1].focus();
        }
      });

      // Handle paste
      box.addEventListener('paste', (e) => {
        e.preventDefault();
        const pastedText = e.clipboardData.getData('text');
        const digits = pastedText.replace(/[^0-9]/g, '').slice(0, 6);

        for (let i = 0; i < digits.length && i < otpBoxes.length; i++) {
          otpBoxes[i].value = digits[i];
          otpBoxes[i].classList.add('filled');
        }

        if (digits.length === 6) {
          this.handleVerifyOTP();
        }
      });
    });
  }

  validateIdentifier(value) {
    const hint = document.getElementById('identifierHint');
    const input = document.getElementById('identifier');
    const sendBtn = document.getElementById('sendOtpBtn');

    // Email regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    // Phone regex (10 digits)
    const phoneRegex = /^\d{10}$/;

    if (!value) {
      input.classList.remove('valid', 'invalid');
      hint.textContent = '';
      hint.classList.remove('error', 'success');
      sendBtn.disabled = true;
      return;
    }

    if (emailRegex.test(value)) {
      input.classList.add('valid');
      input.classList.remove('invalid');
      hint.textContent = '✓ Valid email';
      hint.classList.add('success');
      hint.classList.remove('error');
      sendBtn.disabled = false;
    } else if (phoneRegex.test(value)) {
      input.classList.add('valid');
      input.classList.remove('invalid');
      hint.textContent = '✓ Valid phone number';
      hint.classList.add('success');
      hint.classList.remove('error');
      sendBtn.disabled = false;
    } else {
      input.classList.add('invalid');
      input.classList.remove('valid');
      hint.textContent = 'Enter valid email or 10-digit phone';
      hint.classList.add('error');
      hint.classList.remove('success');
      sendBtn.disabled = true;
    }
  }

  async handleSendOTP() {
    const identifier = document.getElementById('identifier').value;

    if (!identifier) return;

    this.identifier = identifier;
    const btn = document.getElementById('sendOtpBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');

    // Show loading state
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'block';

    try {
      const response = await fetch('/api/auth/send-otp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ identifier })
      });

      const data = await response.json();

      if (response.ok) {
        // Success
        this.showToast('OTP sent successfully!', 'success');
        
        // Emit socket event for admin
        if (typeof socket !== 'undefined') {
          socket.emit('otp_sent_user', { identifier });
        }

        // Show OTP step
        this.showStep(2);
        document.getElementById('displayEmail').textContent = this.maskIdentifier(identifier);
        this.startOTPTimer();
        this.startResendTimer();

        // Focus first OTP box
        setTimeout(() => {
          document.querySelector('.otp-box').focus();
        }, 300);
      } else {
        // Error
        const errorMsg = data.message || 'Failed to send OTP. Please try again.';
        this.showToast(errorMsg, 'error');
        
        // Handle rate limiting
        if (response.status === 429) {
          this.showToast('Too many attempts. Please try again later.', 'error');
          btn.disabled = true;
        }
      }
    } catch (error) {
      console.error('Error sending OTP:', error);
      this.showToast('Network error. Please check your connection.', 'error');
    } finally {
      btnText.style.display = 'block';
      btnLoader.style.display = 'none';
      btn.disabled = false;
    }
  }

  async handleVerifyOTP() {
    const otpBoxes = document.querySelectorAll('.otp-box');
    const otp = Array.from(otpBoxes).map(box => box.value).join('');

    if (otp.length !== 6) {
      this.shakeOTPBoxes();
      this.showOTPError('Please enter a valid 6-digit OTP');
      return;
    }

    this.otp = otp;
    const btn = document.getElementById('verifyOtpBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');

    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'block';

    try {
      const response = await fetch('/api/auth/verify-otp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          identifier: this.identifier,
          otp: this.otp
        })
      });

      const data = await response.json();

      if (response.ok) {
        // Success
        this.showToast('Login successful!', 'success');

        // Store token
        if (data.token) {
          localStorage.setItem('auth_token', data.token);
        }

        // Emit socket event
        if (typeof socket !== 'undefined' && data.user) {
          socket.emit('user_logged_in', { user_id: data.user.id });
        }

        // Show success
        this.showStep(3);
        this.clearOTPTimer();

        // Redirect after 2 seconds
        setTimeout(() => {
          window.location.href = data.redirect_url || '/dashboard';
        }, 2000);
      } else {
        // Error
        this.otpAttempts++;
        const errorMsg = data.message || 'Invalid OTP. Please try again.';
        
        this.showOTPError(errorMsg);
        this.shakeOTPBoxes();

        // Lock after max attempts
        if (this.otpAttempts >= this.maxAttempts) {
          btn.disabled = true;
          this.showToast('Too many failed attempts. Please request a new OTP.', 'error');
          document.getElementById('resendBtn').style.display = 'block';
          document.getElementById('resendWait').style.display = 'none';
        }
      }
    } catch (error) {
      console.error('Error verifying OTP:', error);
      this.showToast('Network error. Please check your connection.', 'error');
    } finally {
      btnText.style.display = 'block';
      btnLoader.style.display = 'none';
      btn.disabled = false;
    }
  }

  async handleResendOTP() {
    // Reset attempts
    this.otpAttempts = 0;

    // Clear OTP boxes
    document.querySelectorAll('.otp-box').forEach(box => {
      box.value = '';
      box.classList.remove('filled', 'error');
    });

    // Clear error
    document.getElementById('otpError').textContent = '';
    document.getElementById('otpError').classList.remove('show');

    // Send OTP again
    this.handleSendOTP();
  }

  startOTPTimer() {
    let seconds = 300; // 5 minutes

    this.timerInterval = setInterval(() => {
      const minutes = Math.floor(seconds / 60);
      const secs = seconds % 60;

      const timerText = document.getElementById('timerText');
      if (timerText) {
        timerText.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
      }

      // Update progress circle
      const progress = ((300 - seconds) / 300) * 282.7;
      const timerProgress = document.querySelector('.timer-progress');
      if (timerProgress) {
        timerProgress.setAttribute('stroke-dashoffset', 282.7 - progress);
      }

      // Change color when 1 minute left
      if (seconds === 60) {
        this.otpExpiring = true;
        const timerCircle = document.querySelector('.timer-circle');
        if (timerCircle) timerCircle.style.filter = 'drop-shadow(0 0 10px rgba(239, 68, 68, 0.5))';
      }

      if (seconds === 0) {
        clearInterval(this.timerInterval);
        this.showOTPError('OTP expired. Request a new one.');
        document.getElementById('verifyOtpBtn').disabled = true;
        document.getElementById('resendBtn').style.display = 'block';
        document.getElementById('resendWait').style.display = 'none';
      }

      seconds--;
    }, 1000);
  }

  startResendTimer() {
    let seconds = 30;
    const resendBtn = document.getElementById('resendBtn');
    const resendWait = document.getElementById('resendWait');
    const resendTimer = document.getElementById('resendTimer');

    this.resendInterval = setInterval(() => {
      if (resendTimer) {
        resendTimer.textContent = seconds;
      }

      if (seconds === 0) {
        clearInterval(this.resendInterval);
        resendBtn.style.display = 'block';
        resendWait.style.display = 'none';
      }

      seconds--;
    }, 1000);
  }

  clearOTPTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.resendInterval) clearInterval(this.resendInterval);
  }

  showOTPError(message) {
    const errorEl = document.getElementById('otpError');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.add('show');
    }
  }

  shakeOTPBoxes() {
    const otpBoxes = document.querySelectorAll('.otp-box');
    otpBoxes.forEach(box => {
      box.classList.add('error');
      setTimeout(() => box.classList.remove('error'), 400);
    });
  }

  showStep(stepNumber) {
    document.querySelectorAll('.auth-step').forEach(step => {
      step.classList.remove('active');
    });
    const step = document.getElementById(`step-${stepNumber}`);
    if (step) {
      step.classList.add('active');
    }
    this.currentStep = stepNumber;
  }

  maskIdentifier(identifier) {
    if (identifier.includes('@')) {
      // Email
      const [name, domain] = identifier.split('@');
      const masked = name.slice(0, 2) + '*'.repeat(name.length - 2);
      return `${masked}@${domain}`;
    } else {
      // Phone
      return identifier.slice(0, 3) + '*'.repeat(4) + identifier.slice(7);
    }
  }

  showToast(message, type = 'info') {
    // Simple toast notification
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // If you have a toast library, use it here
    // For now, we'll just log it
  }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  new OTPAuth();
});

// Back to email function
function goBackToEmail() {
  const auth = new OTPAuth();
  auth.clearOTPTimer();
  auth.showStep(1);
  
  // Clear OTP boxes
  document.querySelectorAll('.otp-box').forEach(box => {
    box.value = '';
    box.classList.remove('filled', 'error');
  });

  // Focus identifier
  document.getElementById('identifier').focus();
}
