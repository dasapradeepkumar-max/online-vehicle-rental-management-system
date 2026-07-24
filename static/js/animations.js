// ANIMATIONS.JS - SCROLL EFFECTS AND ANIMATIONS

// Navbar scroll effect
function initNavbarScroll() {
  const navbar = document.querySelector('.glass-nav');
  if (!navbar) return;

  let lastScrollPosition = 0;

  window.addEventListener('scroll', () => {
    const scrollPosition = window.scrollY;

    // Add scrolled class when user scrolls
    if (scrollPosition > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }

    // Hide/show navbar based on scroll direction
    if (scrollPosition > lastScrollPosition) {
      // Scrolling down
      navbar.style.transform = 'translateY(-100%)';
    } else {
      // Scrolling up
      navbar.style.transform = 'translateY(0)';
    }

    lastScrollPosition = scrollPosition;
  }, { passive: true });
}

// Intersection Observer for scroll animations
function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
  });

  // Observe all sections
  document.querySelectorAll('.vehicles-section, .why-section, .cta-banner').forEach(section => {
    observer.observe(section);
  });

  // Observe vehicle cards
  document.querySelector('#vehicleGrid')?.addEventListener('DOMNodeInserted', () => {
    document.querySelectorAll('.vehicle-card').forEach(card => {
      if (!card.dataset.observed) {
        observer.observe(card);
        card.dataset.observed = 'true';
      }
    });
  });
}

// Smooth scroll for internal links
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href !== '#') {
        e.preventDefault();
        const element = document.querySelector(href);
        if (element) {
          element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      }
    });
  });
}

// Count up animation for stats
function animateCountUp(element, target, duration = 1000) {
  const start = 0;
  const increment = target / (duration / 16); // 16ms per frame (60fps)
  let current = start;

  const counter = setInterval(() => {
    current += increment;
    if (current >= target) {
      element.textContent = target;
      clearInterval(counter);
    } else {
      element.textContent = Math.floor(current);
    }
  }, 16);
}

// Initialize count-up for stats when they come into view
function initStatsAnimation() {
  const statsBar = document.querySelector('.stats-bar');
  if (!statsBar) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !statsBar.dataset.animated) {
        statsBar.dataset.animated = 'true';

        const availableEl = document.getElementById('availableVehicles');
        const rentalsEl = document.getElementById('activeRentals');

        if (availableEl && availableEl.textContent !== '0') {
          const targetAvailable = parseInt(availableEl.textContent) || 42;
          animateCountUp(availableEl, targetAvailable);
        }

        if (rentalsEl && rentalsEl.textContent !== '0') {
          const targetRentals = parseInt(rentalsEl.textContent) || 8;
          animateCountUp(rentalsEl, targetRentals);
        }

        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  observer.observe(statsBar);
}

// Parallax effect for hero section (optional)
function initParallax() {
  const heroSection = document.querySelector('.hero-section');
  if (!heroSection) return;

  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    heroSection.style.backgroundPosition = `0px ${scrolled * 0.5}px`;
  }, { passive: true });
}

// Page load animations
function initPageLoadAnimations() {
  // Fade in body on load
  document.body.style.animation = 'fadeIn 0.5s ease';

  // Add CSS animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }
  `;
  document.head.appendChild(style);
}

// Ripple effect on button clicks (optional)
function initRippleEffect() {
  document.querySelectorAll('.btn-cta, .filter-btn, .vehicle-card-btn').forEach(button => {
    button.addEventListener('click', function(e) {
      const rect = this.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const ripple = document.createElement('span');
      ripple.style.position = 'absolute';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.style.width = '0';
      ripple.style.height = '0';
      ripple.style.borderRadius = '50%';
      ripple.style.background = 'rgba(255, 255, 255, 0.5)';
      ripple.style.pointerEvents = 'none';
      ripple.style.transform = 'translate(-50%, -50%)';
      ripple.style.animation = 'ripple 0.6s ease';

      // Add ripple animation
      const styleEl = document.createElement('style');
      styleEl.textContent = `
        @keyframes ripple {
          to {
            width: 300px;
            height: 300px;
            opacity: 0;
          }
        }
      `;
      if (!document.querySelector('[data-ripple-animation]')) {
        styleEl.setAttribute('data-ripple-animation', 'true');
        document.head.appendChild(styleEl);
      }

      ripple.style.position = 'relative';
      this.style.position = 'relative';
      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });
  });
}

// Initialize all animations on DOM load
document.addEventListener('DOMContentLoaded', function() {
  initPageLoadAnimations();
  initNavbarScroll();
  initScrollAnimations();
  initSmoothScroll();
  initStatsAnimation();
  initParallax();
  initRippleEffect();
});
